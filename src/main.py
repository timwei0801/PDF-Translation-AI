import os
import json
import argparse
import logging
from tqdm import tqdm
from .pdf_processor import PDFProcessor
from .terminology_rag import TerminologyRAG
from .claude_translator import ClaudeTranslator
import time
from pathlib import Path
import fitz  # PyMuPDF

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("translation_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFTranslationSystem:
    """PDF英繁翻譯系統整合"""
    
    def __init__(self, config=None):
        """初始化翻譯系統
        
        Args:
            config: 配置字典或配置文件路徑
        """
        # 載入配置
        self.config = self._load_config(config)
        
        # 初始化組件
        self.pdf_processor = PDFProcessor(pdf_dir=self.config.get("pdf_dir", "raw_pdfs"))
        self.terminology_rag = TerminologyRAG(embedding_model=self.config.get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2"))
        self.translator = ClaudeTranslator(model=self.config.get("claude_model", "claude-3-7-sonnet-20250219"))
        
        # 輸出目錄
        self.output_dir = self.config.get("output_dir", "translated_pdfs")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 載入術語資料庫
        self._load_terminology()
    
    def _load_config(self, config):
        """載入配置"""
        default_config = {
            "pdf_dir": "raw_pdfs",
            "output_dir": "translated_pdfs",
            "terminology_dir": "terminology",
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "claude_model": "claude-3-7-sonnet-20250219",
            "default_domain": "general"
        }
        
        if config is None:
            return default_config
        elif isinstance(config, dict):
            return {**default_config, **config}
        elif isinstance(config, str) and os.path.exists(config):
            with open(config, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            return {**default_config, **user_config}
        else:
            logger.warning("無效的配置，使用默認配置")
            return default_config
    
    def _load_terminology(self):
        """載入術語資料庫"""
        terminology_dir = self.config.get("terminology_dir", "terminology")
        
        if not os.path.exists(terminology_dir):
            logger.info(f"術語目錄 {terminology_dir} 不存在，創建目錄和示例模板")
            os.makedirs(terminology_dir, exist_ok=True)
            
            # 創建術語模板
            self.terminology_rag.create_terminology_template(
                os.path.join(terminology_dir, "template_csv.csv"), 
                format="csv"
            )
            self.terminology_rag.create_terminology_template(
                os.path.join(terminology_dir, "template_json.json"), 
                format="json"
            )
            return
        
        # 載入目錄中的所有術語文件
        loaded = False
        for filename in os.listdir(terminology_dir):
            filepath = os.path.join(terminology_dir, filename)
            
            if not os.path.isfile(filepath):
                continue
                
            if filename.endswith('.csv') or filename.endswith('.json'):
                # 從文件名獲取領域
                domain = os.path.splitext(filename)[0]
                
                # 如果文件名以template開頭，則跳過
                if domain.startswith("template"):
                    continue
                    
                logger.info(f"載入術語文件: {filename}")
                try:
                    self.terminology_rag.add_terminology_file(filepath, domain)
                    loaded = True
                except Exception as e:
                    logger.error(f"載入術語文件 {filename} 失敗: {str(e)}")
        
        if not loaded:
            logger.warning(f"在 {terminology_dir} 中沒有找到有效的術語文件")
    
    def process_pdf(self, pdf_filename):
        """處理單個PDF文件 - 增強版
        
        Args:
            pdf_filename: PDF文件名（不含路徑）
                
        Returns:
            處理結果
        """
        pdf_path = os.path.join(self.config["pdf_dir"], pdf_filename)
        
        if not os.path.exists(pdf_path):
            logger.error(f"文件不存在: {pdf_path}")
            return None
        
        # 創建明確的輸出目錄結構
        output_dir = self.output_dir
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # 記錄路徑信息到日誌
        logger.info(f"輸入PDF路徑: {pdf_path}")
        logger.info(f"輸出目錄: {output_dir}")
        logger.info(f"圖片目錄: {images_dir}")
        
        # 第一步：解析PDF
        logger.info(f"解析PDF: {pdf_filename}")
        pdf_data = self.pdf_processor.process_pdf(pdf_path)
        
        # 新增步驟：專門提取圖片
        logger.info(f"提取圖片: {pdf_filename}")
        images = self.pdf_processor.extract_images(pdf_path)
        pdf_data["images"] = images
        
        # 新增步驟：專門提取表格
        logger.info(f"提取表格: {pdf_filename}")
        tables = self.pdf_processor.extract_tables(pdf_path)
        
        # 按頁面組織表格數據
        table_data = []
        max_page = max([table["page_num"] for table in tables], default=0)
        for page_num in range(1, max_page + 1):
            page_tables = [table for table in tables if table["page_num"] == page_num]
            if page_tables:
                table_data.append({
                    "page_num": page_num,
                    "tables": page_tables
                })
        pdf_data["table_data"] = table_data
        
        # 第二步：確定文檔領域
        domain = self.config.get("default_domain", "general")
        
        # 第三步：翻譯文檔
        logger.info(f"開始翻譯: {pdf_filename}")
        translated_data = self._translate_document(pdf_data, domain)
        
        # 第四步：保存翻譯數據
        json_output = os.path.join(self.output_dir, f"{os.path.splitext(pdf_filename)[0]}_translation_data.json")
        with open(json_output, 'w', encoding='utf-8') as f:
            # 移除無法序列化的部分
            serializable_data = self._prepare_for_serialization(translated_data)
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
        
        # 第五步：修復圖片路徑
        try:
            from .fix_image_paths import fix_image_paths
            fixed_data = fix_image_paths(json_output, save=True)
            logger.info(f"已修復圖片路徑")
        except Exception as e:
            logger.error(f"修復圖片路徑時出錯: {str(e)}")
        
        # 第六步：生成翻譯後的PDF
        output_path = os.path.join(self.output_dir, f"translated_{pdf_filename}")
        try:
            self._generate_translated_pdf(pdf_path, translated_data, output_path)
        except Exception as e:
            logger.error(f"生成PDF時出錯: {str(e)}")
            logger.info(f"翻譯數據已保存到: {json_output}")
                
        # 添加診斷信息
        logger.info("\n=== 診斷信息 ===")
        logger.info(f"處理的PDF文件: {pdf_filename}")
        logger.info(f"輸出JSON文件: {json_output}")
        
        # 檢查圖片
        image_count = len(translated_data.get("images", []))
        logger.info(f"提取的圖片數量: {image_count}")
        
        # 檢查表格
        table_pages = len(translated_data.get("table_data", []))
        table_count = sum(len(page.get("tables", [])) for page in translated_data.get("table_data", []))
        logger.info(f"提取的表格頁數: {table_pages}")
        logger.info(f"提取的表格數量: {table_count}")
        
        # 檢查圖片文件
        images_dir = os.path.join(self.output_dir, "images")
        if os.path.exists(images_dir):
            image_files = len([f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))])
            logger.info(f"圖片目錄中的文件數量: {image_files}")
        
        logger.info("=== 診斷結束 ===\n")
        
        return {
            "original_pdf": pdf_filename,
            "translated_pdf": f"translated_{pdf_filename}",
            "translation_data": json_output,
            "image_count": image_count,
            "table_count": table_count
        }
    
    def _translate_document(self, pdf_data, domain):
        """翻譯文檔內容
        
        Args:
            pdf_data: PDF解析數據
            domain: 文檔領域
            
        Returns:
            翻譯後的數據
        """
        # 複製原始數據結構
        translated_data = pdf_data.copy()
        
        # 獲取術語資料庫（如果有）
        terminology_db = self.terminology_rag.terminology_db if hasattr(self.terminology_rag, "terminology_db") else None
        
        # 處理每一頁
        for page_idx, page in enumerate(tqdm(pdf_data["text_data"], desc="翻譯頁面")):
            # 翻譯文本塊
            if "blocks" in page:
                translated_blocks = self.translator.translate_document_section(
                    page["blocks"],
                    terminology_db,
                    domain
                )
                translated_data["text_data"][page_idx]["blocks"] = translated_blocks
        
        # 處理表格
        for page_idx, page in enumerate(pdf_data["table_data"]):
            if "tables" in page and page["tables"]:
                translated_tables = []
                for table in page["tables"]:
                    translated_table = self.translator.translate_table(table)
                    translated_tables.append(translated_table)
                translated_data["table_data"][page_idx]["tables"] = translated_tables
        
        # 處理圖像中的文字
        for img_idx, img_info in enumerate(pdf_data["images"]):
            if "text_in_image" in img_info and img_info["text_in_image"]:
                text_in_image = img_info["text_in_image"]
                translated_text = self.translator.translate_image_text(text_in_image)
                translated_data["images"][img_idx]["text_in_image_translated"] = translated_text
        
        return translated_data
    
    def _generate_translated_pdf(self, original_pdf_path, translated_data, output_path):
        """生成翻譯後的PDF
        
        Args:
            original_pdf_path: 原始PDF路徑
            translated_data: 翻譯後的數據
            output_path: 輸出PDF路徑
        """
        logger.info(f"生成翻譯後的PDF: {output_path}")
        
        # 使用PyMuPDF生成新的PDF
        src_doc = fitz.open(original_pdf_path)
        dst_doc = fitz.open()
        
        # 首先，複製原始PDF的所有頁面
        for page_idx in range(len(src_doc)):
            dst_doc.new_page(width=src_doc[page_idx].rect.width, height=src_doc[page_idx].rect.height * 2)
        
        # 對每一頁添加翻譯
        for page_idx, page in enumerate(translated_data["text_data"]):
            # 獲取目標頁面
            dst_page = dst_doc[page_idx]
            
            # 複製原始頁面內容 - 修改這部分代碼
            src_page = src_doc[page_idx]
            # 創建一個矩形區域來放置原始頁面內容
            rect = fitz.Rect(0, 0, dst_page.rect.width, src_page.rect.height)
            dst_page.show_pdf_page(rect, src_doc, page_idx)
            
            # 在下方添加翻譯內容
            translation_rect = fitz.Rect(0, src_page.rect.height, dst_page.rect.width, dst_page.rect.height)
            
            # 添加分隔線
            dst_page.draw_line(
                fitz.Point(0, src_page.rect.height),
                fitz.Point(dst_page.rect.width, src_page.rect.height),
                color=(0, 0, 0),
                width=1
            )
            
            # 添加"中文翻譯"標題
            title_rect = fitz.Rect(10, src_page.rect.height + 10, dst_page.rect.width - 10, src_page.rect.height + 30)
            dst_page.insert_text(title_rect.tl, "中文翻譯", fontsize=12, color=(0, 0, 0))
            
            # 添加翻譯文本
            text_y = src_page.rect.height + 40
            for block in page.get("blocks", []):
                if "content_translated" in block:
                    text = block["content_translated"]
                    rect = fitz.Rect(20, text_y, dst_page.rect.width - 20, text_y + 1000)  # 高度足夠大
                    text_height = dst_page.insert_text(rect, text, fontsize=10, color=(0, 0, 0))
                    text_y += text_height + 10
        
        # 保存新的PDF
        dst_doc.save(output_path)
        dst_doc.close()
        src_doc.close()
        
        logger.info(f"已生成翻譯PDF: {output_path}")
    
    def _prepare_for_serialization(self, data):
        """準備數據以便JSON序列化
        
        Args:
            data: 原始數據
            
        Returns:
            可序列化的數據
        """
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                # 跳過無法序列化的部分
                if k == "image" or k == "PIL_image":
                    continue
                result[k] = self._prepare_for_serialization(v)
            return result
        elif isinstance(data, list):
            return [self._prepare_for_serialization(item) for item in data]
        else:
            return data
    
    def process_all_pdfs(self):
        """處理所有PDF文件"""
        pdf_files = self.pdf_processor.get_pdf_files()
        
        if not pdf_files:
            logger.warning(f"在 {self.config['pdf_dir']} 中沒有找到PDF文件")
            return []
        
        results = []
        for pdf_file in pdf_files:
            pdf_filename = os.path.basename(pdf_file)
            result = self.process_pdf(pdf_filename)
            if result:
                results.append(result)
        
        # 記錄API使用統計
        usage_stats = self.translator.get_usage_statistics()
        stats_path = os.path.join(self.output_dir, "translation_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(usage_stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"處理完成，共翻譯 {len(results)} 個PDF文件")
        logger.info(f"API使用統計：總請求數 {usage_stats['total_requests']}，總輸入字符數 {usage_stats['total_input_chars']}，總輸出字符數 {usage_stats['total_output_chars']}")
        
        return results
    
    def extract_terms_from_pdfs(self, max_pdfs=3, terms_per_pdf=50):
        """從PDF文件中提取可能的術語
        
        Args:
            max_pdfs: 最大處理的PDF文件數量
            terms_per_pdf: 每個PDF提取的術語數量
            
        Returns:
            提取的術語列表
        """
        logger.info("從PDF中提取術語...")
        
        extracted_terms = []
        pdf_files = self.pdf_processor.get_pdf_files()[:max_pdfs]
        
        for pdf_file in pdf_files:
            logger.info(f"從 {os.path.basename(pdf_file)} 提取術語")
            
            # 處理PDF
            pdf_data = self.pdf_processor.process_pdf(pdf_file)
            
            # 提取所有英文文本
            all_text = ""
            for page in pdf_data["text_data"]:
                for block in page.get("blocks", []):
                    if block.get("type") == "text":
                        all_text += block.get("content", "") + " "
            
            # 使用术語RAG提取
            pdf_terms = []
            
            # 分段處理，避免文本過長
            chunk_size = 5000
            chunks = [all_text[i:i+chunk_size] for i in range(0, len(all_text), chunk_size)]
            
            for chunk in chunks:
                # 使用通用方法提取可能的術語
                import re
                
                # 1. 提取可能的專業術語（大寫開頭的連續多個單詞）
                capitalized_terms = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', chunk)
                
                # 2. 提取括號中的縮寫及其前面的詞組
                abbreviations = re.findall(r'\b([A-Za-z ]+)\s+\(([A-Z]{2,})\)', chunk)
                
                # 3. 提取連字符連接的術語
                hyphenated_terms = re.findall(r'\b([A-Za-z]+(?:-[A-Za-z]+)+)\b', chunk)
                
                # 合併提取結果
                for term in capitalized_terms + [t[0] for t in abbreviations] + hyphenated_terms:
                    if len(term.split()) >= 2 and len(term) > 5:  # 只考慮多詞術語且長度超過5
                        pdf_terms.append(term.strip())
            
            # 獲取出現次數最多的術語
            from collections import Counter
            term_counter = Counter(pdf_terms)
            most_common_terms = [term for term, _ in term_counter.most_common(terms_per_pdf)]
            
            # 翻譯這些術語
            for term in most_common_terms:
                translation = self.translator.translate_text(term)
                extracted_terms.append({
                    "english": term,
                    "chinese": translation.strip(),
                    "source_pdf": os.path.basename(pdf_file)
                })
        
        # 保存提取的術語
        output_file = os.path.join(self.config.get("terminology_dir", "terminology"), "extracted_terms.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_terms, f, ensure_ascii=False, indent=2)
            
        logger.info(f"已提取 {len(extracted_terms)} 個術語，並保存至 {output_file}")
        
        return extracted_terms
    
    def create_translation_summary(self, results):
        """創建翻譯摘要報告
        
        Args:
            results: 處理結果列表
            
        Returns:
            摘要報告路徑
        """
        summary = {
            "translation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_pdfs": len(results),
            "processed_files": results,
            "api_usage": self.translator.get_usage_statistics()
        }
        
        summary_path = os.path.join(self.output_dir, "translation_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
        logger.info(f"已生成翻譯摘要：{summary_path}")
        
        return summary_path

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="PDF英繁翻譯系統")
    parser.add_argument("--config", type=str, help="配置文件路徑")
    parser.add_argument("--pdf", type=str, help="要處理的單個PDF文件名")
    parser.add_argument("--extract-terms", action="store_true", help="從PDF中提取術語")
    args = parser.parse_args()
    
    # 載入配置
    config = None
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 初始化系統
    system = PDFTranslationSystem(config)
    
    # 提取術語
    if args.extract_terms:
        system.extract_terms_from_pdfs()
        return
    
    # 處理單個PDF或所有PDF
    if args.pdf:
        result = system.process_pdf(args.pdf)
        if result:
            logger.info(f"已處理文件：{args.pdf}")
            logger.info(f"翻譯結果保存在：{result['translated_pdf']}")
    else:
        results = system.process_all_pdfs()
        if results:
            summary_path = system.create_translation_summary(results)
            logger.info(f"所有文件處理完成，摘要報告：{summary_path}")

if __name__ == "__main__":
    main()