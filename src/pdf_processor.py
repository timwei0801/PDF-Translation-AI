import os
import re
import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import numpy as np
import pytesseract  # 用於OCR
from langdetect import detect  # 語言檢測

class PDFProcessor:
    def __init__(self, pdf_dir="raw_pdfs"):
        """初始化PDF處理器
        
        Args:
            pdf_dir: PDF文件所在的目錄
        """
        self.pdf_dir = pdf_dir
        self.processed_data = {}
        
    def get_pdf_files(self):
        """獲取目錄中所有PDF文件的路徑"""
        pdf_files = []
        for file in os.listdir(self.pdf_dir):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(self.pdf_dir, file))
        return pdf_files
    
    def extract_text_with_pymupdf(self, pdf_path):
        """使用PyMuPDF提取PDF文本，保留基本結構"""
        doc = fitz.open(pdf_path)
        text_data = []
        
        for page_num, page in enumerate(doc):
            # 提取頁面文本
            text = page.get_text("dict")
            blocks = text["blocks"]
            
            page_data = {
                "page_num": page_num + 1,
                "blocks": []
            }
            
            for block in blocks:
                if "lines" in block:  # 文本塊
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"] + " "
                    
                    # 判斷是否可能是公式（簡單啟發式方法）
                    is_formula = self._check_if_formula(block_text)
                    
                    page_data["blocks"].append({
                        "type": "formula" if is_formula else "text",
                        "content": block_text.strip(),
                        "bbox": block["bbox"]  # 座標，用於之後重建結構
                    })
                elif "image" in block:  # 圖像塊
                    # 儲存圖像以供後續處理
                    image_data = {
                        "type": "image",
                        "bbox": block["bbox"],
                        "image": block["image"]  # 圖像數據
                    }
                    page_data["blocks"].append(image_data)
            
            text_data.append(page_data)
        
        doc.close()
        return text_data
    
    def extract_text_with_pdfplumber(self, pdf_path):
        """使用pdfplumber提取文本，更適合表格處理"""
        with pdfplumber.open(pdf_path) as pdf:
            text_data = []
            
            for page_num, page in enumerate(pdf.pages):
                # 提取表格
                tables = page.extract_tables()
                
                # 提取文字
                text = page.extract_text()
                
                page_data = {
                    "page_num": page_num + 1,
                    "text": text,
                    "tables": tables
                }
                
                text_data.append(page_data)
                
        return text_data
    
    def extract_images(self, pdf_path):
        """從PDF中提取並保存所有圖片 - 增強版
        
        Args:
            pdf_path: PDF文件路徑
                
        Returns:
            提取的圖片信息列表
        """
        images = []
        
        # 創建圖片保存目錄（與HTML文件在同一目錄）
        output_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        # 創建輸出目錄結構
        output_dir = os.path.join(os.path.dirname(os.path.dirname(pdf_path)), "translated_pdfs")
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        print(f"圖片將被保存到: {images_dir}")
        
        # 打開PDF
        doc = fitz.open(pdf_path)
        
        # 處理每一頁
        for page_idx, page in enumerate(doc):
            # 獲取頁面上的圖片
            image_list = page.get_images(full=True)
            
            for img_idx, img in enumerate(image_list):
                try:
                    # 提取圖片
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # 確定圖片類型
                    ext = base_image["ext"]
                    
                    # 創建圖片文件名和保存路徑
                    img_filename = f"{output_basename}_page{page_idx+1}_img{img_idx+1}.{ext}"
                    img_path = os.path.join(images_dir, img_filename)
                    
                    # 保存圖片
                    with open(img_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    # 獲取圖片在頁面中的位置
                    bbox = page.get_image_bbox(img)
                    
                    # 尋找圖片附近的可能圖表標題
                    caption = self._find_image_caption(page, bbox)
                    
                    # 添加圖片信息
                    images.append({
                        "type": "image",
                        "page_num": page_idx + 1,
                        "img_index": img_idx,
                        "bbox": [float(coord) for coord in bbox],
                        "image_path": os.path.join("images", img_filename),  # 使用相對路徑
                        "caption": caption
                    })
                    
                    print(f"已提取並保存圖片: {img_path}")
                    
                except Exception as e:
                    print(f"處理圖片時出錯: {e}")
            
            # 新增部分：檢測頁面中無法直接提取的圖表
            try:
                # 查找可能含有"Figure"或"Table"字樣的文本塊
                text_blocks = page.get_text("dict")["blocks"]
                for block_idx, block in enumerate(text_blocks):
                    if "lines" in block:
                        block_text = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                block_text += span["text"] + " "
                        
                        # 檢查是否是圖表標題
                        if re.search(r'(figure|fig\.?|圖)\s*\d+', block_text, re.IGNORECASE):
                            # 這個塊可能是圖表標題，檢查上方的區域
                            caption = block_text.strip()
                            x0, y0, x1, y1 = block["bbox"]
                            
                            # 假設圖表在標題上方約200-300像素
                            figure_area = (x0-50, max(0, y0-300), x1+50, y0-5)
                            
                            # 創建截圖文件名
                            fig_filename = f"{output_basename}_page{page_idx+1}_fig{block_idx}.png"
                            fig_path = os.path.join(images_dir, fig_filename)
                            
                            # 使用PyMuPDF的pixmap對象截取這個區域
                            try:
                                pix = page.get_pixmap(clip=figure_area, matrix=fitz.Matrix(2, 2))
                                pix.save(fig_path)
                                
                                # 添加到圖片列表
                                images.append({
                                    "type": "figure",
                                    "page_num": page_idx + 1,
                                    "img_index": 1000 + block_idx,  # 避免與直接提取的圖片索引衝突
                                    "bbox": [float(coord) for coord in figure_area],
                                    "image_path": os.path.join("images", fig_filename),
                                    "caption": caption
                                })
                                print(f"已提取可能的圖表區域: {fig_path}")
                            except Exception as e:
                                print(f"截取圖表區域時出錯: {e}")
            except Exception as e:
                print(f"尋找頁面中的圖表區域時出錯: {e}")
        
        doc.close()
        return images
    
    def extract_tables(self, pdf_path):
        """從PDF中提取所有表格
        
        Args:
            pdf_path: PDF文件路徑
                
        Returns:
            提取的表格信息列表
        """
        tables = []
        
        try:
            # 使用pdfplumber提取表格
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    # 提取表格
                    extracted_tables = page.extract_tables()
                    
                    if extracted_tables:
                        for table_idx, table_data in enumerate(extracted_tables):
                            # 過濾空行和空單元格
                            filtered_table = []
                            for row in table_data:
                                if any(cell and str(cell).strip() for cell in row):
                                    filtered_row = [str(cell).strip() if cell else "" for cell in row]
                                    filtered_table.append(filtered_row)
                            
                            if filtered_table:
                                # 嘗試查找表格標題
                                caption = self._find_table_caption(page, table_idx)
                                
                                # 添加表格信息
                                tables.append({
                                    "type": "table",
                                    "page_num": page_idx + 1,
                                    "table_idx": table_idx,
                                    "data": filtered_table,
                                    "has_header": True,  # 通常第一行為表頭
                                    "caption": caption
                                })
                                
                                print(f"已提取表格: 頁面 {page_idx+1}, 表格 {table_idx}")
        except Exception as e:
            print(f"使用pdfplumber提取表格時出錯: {str(e)}")
        
        # 如果pdfplumber未能提取表格，嘗試使用PyMuPDF
        if not tables:
            try:
                doc = fitz.open(pdf_path)
                for page_idx, page in enumerate(doc):
                    # 使用PyMuPDF的表格檢測功能
                    tab = page.find_tables()
                    if tab and tab.tables:
                        for table_idx, table in enumerate(tab.tables):
                            # 從表格單元格中提取數據
                            table_data = []
                            
                            # 按行組織單元格
                            rows = {}
                            for cell in table.cells:
                                row_key = round(cell.y0)  # 使用y0坐標作為行標識
                                if row_key not in rows:
                                    rows[row_key] = []
                                
                                # 獲取單元格文本
                                text = page.get_text("text", clip=cell.rect).strip()
                                rows[row_key].append((cell.x0, text))  # 保存x坐標以便後續排序
                            
                            # 按行y坐標排序並創建表格數據
                            for row_y in sorted(rows.keys()):
                                # 按x坐標排序單元格
                                cells = rows[row_y]
                                cells.sort(key=lambda c: c[0])
                                
                                row_data = [text for _, text in cells]
                                if any(text.strip() for text in row_data):  # 確保行不是空的
                                    table_data.append(row_data)
                            
                            if table_data:
                                # 尋找表格標題
                                caption = self._find_table_caption(page, table_idx)
                                
                                tables.append({
                                    "type": "table",
                                    "page_num": page_idx + 1,
                                    "table_idx": table_idx,
                                    "data": table_data,
                                    "has_header": True,
                                    "caption": caption
                                })
                                
                                print(f"已使用PyMuPDF提取表格: 頁面 {page_idx+1}, 表格 {table_idx}")
                
                doc.close()
            except Exception as e:
                print(f"使用PyMuPDF提取表格時出錯: {str(e)}")
        
        return tables
    
    def _find_table_caption(self, page, table_idx):
        """查找表格的標題
        
        Args:
            page: PDF頁面對象
            table_idx: 表格索引
            
        Returns:
            可能的表格標題
        """
        try:
            # 獲取頁面文本
            text = ""
            if hasattr(page, 'extract_text'):  # pdfplumber頁面
                text = page.extract_text()
            else:  # PyMuPDF頁面
                text = page.get_text("text")
            
            # 尋找各種形式的表格標題
            patterns = [
                r'Table\s+\d+[\.\:]\s*([^\n]+)',
                r'Table\s+\d+\s+([^\n]+)',
                r'表\s*\d+[\.\:]\s*([^\n]+)',
                r'Tab\.\s*\d+[\.\:]\s*([^\n]+)'
            ]
            
            # 查找所有匹配
            all_matches = []
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                all_matches.extend([(m.start(), m.group(0)) for m in matches])
            
            # 按位置排序
            all_matches.sort()
            
            # 嘗試找到對應這個表格的標題
            if table_idx < len(all_matches):
                return all_matches[table_idx][1].strip()
        except Exception as e:
            print(f"查找表格標題時出錯: {e}")
        
        return ""
    
    def _find_image_caption(self, page, bbox):
        """查找圖片附近的標題文本
        
        Args:
            page: PDF 頁面對象
            bbox: 圖片邊界框
            
        Returns:
            可能的圖片標題文本
        """
        x0, y0, x1, y1 = bbox
        
        # 檢查圖片下方的文本 (常見的圖表標題位置)
        below_text = page.get_text("text", clip=(x0, y1, x1, y1 + 50))
        if below_text and re.search(r'(figure|fig\.?|圖)\s*\d+', below_text, re.IGNORECASE):
            return below_text.strip()
        
        # 檢查圖片上方的文本
        above_text = page.get_text("text", clip=(x0, max(0, y0 - 50), x1, y0))
        if above_text and re.search(r'(figure|fig\.?|圖)\s*\d+', above_text, re.IGNORECASE):
            return above_text.strip()
        
        return ""
    
    def _check_if_formula(self, text):
        """簡單檢查文本是否可能是數學公式"""
        # 數學符號的簡單檢測
        math_symbols = ['∫', '∑', '∏', '√', '≈', '≠', '≤', '≥', '±', '∞', '∂', '∇', '∆', '∈', '∉', '∩', '∪']
        formula_indicators = ['=', '+', '-', '*', '/', '^', '(', ')', '[', ']', '{', '}']
        
        # 檢查LaTeX風格的公式標記
        if '\\begin{equation}' in text or '\\end{equation}' in text:
            return True
        
        # 檢查常見數學符號
        symbol_count = sum(1 for symbol in math_symbols if symbol in text)
        indicator_count = sum(1 for indicator in formula_indicators if indicator in text)
        
        # 如果包含多個數學符號和指標，可能是公式
        if (symbol_count > 0) or (indicator_count > 3 and len(text) < 100):
            return True
            
        return False
    
    def detect_language(self, text):
        """檢測文本語言"""
        try:
            return detect(text)
        except:
            return "unknown"
    
    def process_pdf(self, pdf_path):
        """處理單個 PDF 文件
        
        Args:
            pdf_path: PDF 文件路徑
            
        Returns:
            處理結果字典
        """
        filename = os.path.basename(pdf_path)
        print(f"處理 {filename}...")
        
        # 提取文本和結構
        text_data = self.extract_text_with_pymupdf(pdf_path)
        
        # 提取表格
        table_data = self.extract_text_with_pdfplumber(pdf_path)
        
        # 提取圖像 - 使用修改後的方法
        images = self.extract_images(pdf_path)
        
        # 組織結果
        result = {
            "filename": filename,
            "text_data": text_data,
            "table_data": table_data,
            "images": images
        }
        
        # 檢測文檔主要語言
        all_text = ""
        for page in text_data:
            for block in page["blocks"]:
                if block["type"] == "text":
                    all_text += block["content"] + " "
        
        if all_text:
            result["primary_language"] = self.detect_language(all_text[:1000])
        else:
            result["primary_language"] = "unknown"
        
        self.processed_data[filename] = result
        return result
    
    def _detect_tables(self, page):
        """檢測頁面中的表格
        
        Args:
            page: 頁面對象
            
        Returns:
            表格列表
        """
        tables = []
        
        # 使用 PyMuPDF 的表格檢測功能
        try:
            tab = page.find_tables()
            if tab and tab.tables:
                for idx, table in enumerate(tab.tables):
                    # 創建 HTML 表格
                    table_html = "<table class='table'>"
                    
                    # 添加表頭
                    if len(table.cells) > 0:
                        first_row_y0 = min(cell.y0 for cell in table.cells)
                        header_cells = [cell for cell in table.cells if abs(cell.y0 - first_row_y0) < 2]
                        if header_cells:
                            table_html += "<thead><tr>"
                            header_cells.sort(key=lambda cell: cell.x0)
                            for cell in header_cells:
                                text = page.get_text("text", clip=cell.rect)
                                table_html += f"<th>{text.strip()}</th>"
                            table_html += "</tr></thead>"
                    
                    # 添加表體
                    table_html += "<tbody>"
                    rows = {}
                    for cell in table.cells:
                        # 跳過已處理的表頭
                        if cell in header_cells:
                            continue
                        
                        # 按行分組
                        row_key = round(cell.y0)  # 四捨五入以處理輕微的對齊偏差
                        if row_key not in rows:
                            rows[row_key] = []
                        
                        text = page.get_text("text", clip=cell.rect)
                        rows[row_key].append((cell.x0, text.strip()))
                    
                    # 對每一行的單元格按水平位置排序
                    for row_y in sorted(rows.keys()):
                        cells = rows[row_y]
                        cells.sort(key=lambda c: c[0])
                        
                        table_html += "<tr>"
                        for _, text in cells:
                            table_html += f"<td>{text}</td>"
                        table_html += "</tr>"
                    
                    table_html += "</tbody></table>"
                    
                    # 尋找表格附近的標題
                    caption = self._find_table_caption(page, table.bbox)
                    
                    tables.append({
                        "type": "table",
                        "bbox": [float(coord) for coord in table.bbox],
                        "content": table_html,
                        "caption": caption
                    })
        except Exception as e:
            print(f"檢測表格時出錯: {e}")
        
        return tables

    def _find_table_caption(self, page, bbox):
        """尋找表格附近的標題
        
        Args:
            page: 頁面對象
            bbox: 表格邊界框
            
        Returns:
            可能的表格標題
        """
        x0, y0, x1, y1 = bbox
        
        # 檢查表格上方的文本 (常見的表格標題位置)
        above_text = page.get_text("text", clip=(x0, max(0, y0 - 50), x1, y0))
        if above_text and re.search(r'(table|tab\.?|表)\s*\d+', above_text, re.IGNORECASE):
            return above_text.strip()
        
        # 檢查表格下方的文本
        below_text = page.get_text("text", clip=(x0, y1, x1, y1 + 50))
        if below_text and re.search(r'(table|tab\.?|表)\s*\d+', below_text, re.IGNORECASE):
            return below_text.strip()
        
        return ""
    
    def process_all_pdfs(self):
        """處理目錄中所有PDF文件"""
        pdf_files = self.get_pdf_files()
        for pdf_file in pdf_files:
            self.process_pdf(pdf_file)
        
        print(f"已處理 {len(pdf_files)} 個PDF文件")
        return self.processed_data

# 使用示例
if __name__ == "__main__":
    processor = PDFProcessor(pdf_dir="raw_pdfs")
    processed_data = processor.process_all_pdfs()
    
    # 輸出處理結果摘要
    for filename, data in processed_data.items():
        print(f"文件: {filename}")
        print(f"主要語言: {data['primary_language']}")
        print(f"頁數: {len(data['text_data'])}")
        
        text_blocks = sum(len([b for b in page['blocks'] if b['type'] == 'text']) 
                         for page in data['text_data'])
        formula_blocks = sum(len([b for b in page['blocks'] if b['type'] == 'formula']) 
                            for page in data['text_data'])
        image_count = len(data['images'])
        
        print(f"文本塊數量: {text_blocks}")
        print(f"公式數量: {formula_blocks}")
        print(f"圖像數量: {image_count}")
        print("-" * 50)