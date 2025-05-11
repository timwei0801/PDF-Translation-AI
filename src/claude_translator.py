import os
import json
import time
import anthropic
import re
import tqdm
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 載入環境變數（API密鑰）
load_dotenv()

class ClaudeTranslator:
    """使用Claude API的專業文獻翻譯系統"""
    
    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初始化Claude翻譯器
        
        Args:
            api_key: Anthropic API密鑰（如果為None，則從環境變數中獲取）
            model: 使用的Claude模型名稱
        """
        # 獲取API密鑰
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("需要Anthropic API密鑰")
            
        # 初始化Claude客戶端
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        
        # 請求記錄
        self.request_history = []
        
        # 計數器，用於限制API調用速率
        self.request_counter = 0
        self.last_request_time = time.time()
        
        # 術語記憶，保持翻譯一致性
        self.term_memory = {}
    
    def translate_text(self, 
                      text: str, 
                      terminology_db: Optional[Dict] = None,
                      domain: Optional[str] = None) -> str:
        """翻譯普通文本
        
        Args:
            text: 要翻譯的英文文本
            terminology_db: 專業術語資料庫（可選）
            domain: 文本所屬領域（可選）
            
        Returns:
            翻譯後的中文文本
        """
        # 檢查文本是否為空
        if not text or text.strip() == "":
            return ""
            
        # 檢查是否已翻譯過相同或極為相似的文本
        # 使用文本的前50個字符作為指紋
        text_fingerprint = text[:50] if len(text) > 50 else text
        
        if text_fingerprint in self.term_memory:
            return self.term_memory[text_fingerprint]
        
        # 限制API調用速率
        self._rate_limit()
        
        # 準備提示
        prompt = self._create_translation_prompt(text, terminology_db, domain)
        
        # 調用Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取翻譯結果
            translated_text = response.content[0].text
            
            # 清理翻譯結果，移除可能的格式化元素
            translated_text = self._clean_translation(translated_text)
            
            # 記錄請求
            self.request_history.append({
                "timestamp": time.time(),
                "input_length": len(text),
                "output_length": len(translated_text),
                "domain": domain,
                "model": self.model
            })
            
            # 儲存到術語記憶
            self.term_memory[text_fingerprint] = translated_text
            
            return translated_text
            
        except Exception as e:
            print(f"翻譯時出錯: {str(e)}")
            return ""
    
    def _clean_translation(self, text: str) -> str:
        """清理翻譯結果，移除可能的格式化元素"""
        # 移除可能的前綴說明
        text = re.sub(r'^(翻譯結果[:：]|Translation[:：]|\[Translation\])\s*', '', text)
        
        # 移除可能的Markdown代碼塊格式
        text = re.sub(r'```\w*\n?', '', text)
        text = re.sub(r'```\s*$', '', text)
        
        # 移除可能的引用格式
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def translate_formula(self, formula: str) -> str:
        """翻譯數學公式（保留公式結構，僅翻譯文字部分）
        
        Args:
            formula: 包含數學公式的文本
            
        Returns:
            翻譯後的公式
        """
        # 檢查是否為空
        if not formula or formula.strip() == "":
            return ""
        
        # 檢查快取
        if formula in self.term_memory:
            return self.term_memory[formula]
        
        # 限制API調用速率
        self._rate_limit()
        
        # 創建專門用於公式翻譯的提示
        prompt = f"""
請將以下包含數學公式的英文文本翻譯成繁體中文。請注意：

1. 保留所有數學符號、變數名稱和公式結構不變
2. 只翻譯公式中的英文文字部分（如"where"、"for all"等）
3. 對於變數的定義說明，請翻譯成中文
4. 完全保留LaTeX格式和符號

以下是需要翻譯的公式文本：

{formula}

請輸出翻譯結果，不需要任何解釋。
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取翻譯結果
            translated_formula = response.content[0].text
            
            # 清理翻譯結果
            translated_formula = self._clean_translation(translated_formula)
            
            # 記錄請求
            self.request_history.append({
                "timestamp": time.time(),
                "input_length": len(formula),
                "output_length": len(translated_formula),
                "type": "formula",
                "model": self.model
            })
            
            # 儲存到術語記憶
            self.term_memory[formula] = translated_formula
            
            return translated_formula
            
        except Exception as e:
            print(f"翻譯公式時出錯: {str(e)}")
            return formula  # 出錯時返回原始公式
    
    def translate_image_text(self, text_in_image: str) -> str:
        """翻譯圖像中的文字
        
        Args:
            text_in_image: 從圖像中提取的英文文本
            
        Returns:
            翻譯後的中文文本
        """
        # 檢查是否為空
        if not text_in_image or text_in_image.strip() == "":
            return ""
        
        # 檢查快取
        if text_in_image in self.term_memory:
            return self.term_memory[text_in_image]
        
        # 限制API調用速率
        self._rate_limit()
        
        # 創建專門用於圖像文字翻譯的提示
        prompt = f"""
請將以下從圖像中提取的英文文本翻譯成繁體中文：

{text_in_image}

請直接輸出翻譯結果，不需要任何解釋。如果文本不完整或無法理解，請盡量根據上下文進行合理翻譯。
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取翻譯結果
            translated_text = response.content[0].text
            
            # 清理翻譯結果
            translated_text = self._clean_translation(translated_text)
            
            # 記錄請求
            self.request_history.append({
                "timestamp": time.time(),
                "input_length": len(text_in_image),
                "output_length": len(translated_text),
                "type": "image_text",
                "model": self.model
            })
            
            # 儲存到術語記憶
            self.term_memory[text_in_image] = translated_text
            
            return translated_text
            
        except Exception as e:
            print(f"翻譯圖像文字時出錯: {str(e)}")
            return text_in_image  # 出錯時返回原始文本
    
    def translate_table(self, table_data: List[List[str]]) -> List[List[str]]:
        """翻譯表格數據
        
        Args:
            table_data: 表格數據，二維列表，每個元素是一個單元格的文本
            
        Returns:
            翻譯後的表格數據
        """
        # 檢查是否為空
        if not table_data or len(table_data) == 0:
            return []
        
        # 創建表格指紋
        table_fingerprint = str(table_data[:2])  # 使用前兩行作為指紋
        if table_fingerprint in self.term_memory:
            return self.term_memory[table_fingerprint]
        
        # 限制API調用速率
        self._rate_limit()
        
        # 將表格轉換為JSON字符串
        table_json = json.dumps(table_data, ensure_ascii=False)
        
        # 創建專門用於表格翻譯的提示
        prompt = f"""
請將以下JSON格式的表格數據從英文翻譯成繁體中文。表格結構是一個二維陣列，每個元素是單元格的文本內容：

```json
{table_json}
請遵循以下規則：

直接輸出翻譯後的JSON格式表格數據，保持原始結構不變
僅翻譯文本內容，不翻譯專有名詞、縮寫和數值
保持表格標題和專業術語的準確性
返回完整的JSON陣列，不要有額外文字

請直接返回JSON格式的翻譯結果，不需要任何解釋或說明。
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 提取翻譯結果
            result_text = response.content[0].text
            
            # 提取JSON部分
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果沒有找到JSON標記，嘗試直接解析整個響應
                json_str = result_text.strip()
            
            # 清理JSON字符串
            json_str = re.sub(r'^[\s\n]*', '', json_str)  # 移除開頭的空白和換行
            json_str = re.sub(r'[\s\n]*$', '', json_str)  # 移除結尾的空白和換行
            
            # 解析JSON
            try:
                translated_table = json.loads(json_str)
                
                # 驗證表格結構
                if not isinstance(translated_table, list) or not all(isinstance(row, list) for row in translated_table):
                    raise ValueError("翻譯後的表格結構無效")
                
                # 記錄請求
                self.request_history.append({
                    "timestamp": time.time(),
                    "input_cells": sum(len(row) for row in table_data),
                    "output_cells": sum(len(row) for row in translated_table),
                    "type": "table",
                    "model": self.model
                })
                
                # 儲存到術語記憶
                self.term_memory[table_fingerprint] = translated_table
                
                return translated_table
            except json.JSONDecodeError as e:
                print(f"無法解析翻譯後的表格JSON: {e}")
                # 嘗試修復JSON
                try:
                    # 嘗試修復常見的JSON問題
                    fixed_json = re.sub(r"'", '"', json_str)  # 將單引號替換為雙引號
                    fixed_json = re.sub(r",\s*]", "]", fixed_json)  # 移除尾部逗號
                    fixed_json = re.sub(r",\s*}", "}", fixed_json)  # 移除尾部逗號
                    translated_table = json.loads(fixed_json)
                    return translated_table
                except:
                    return table_data
            
        except Exception as e:
            print(f"翻譯表格時出錯: {str(e)}")
            return table_data  # 出錯時返回原始表格

    def _create_translation_prompt(self, 
                                text: str, 
                                terminology_db: Optional[Dict] = None,
                                domain: Optional[str] = None) -> str:
        """創建翻譯提示
        
        Args:
            text: 要翻譯的文本
            terminology_db: 專業術語資料庫
            domain: 文本所屬領域
            
        Returns:
            格式化的提示文本
        """
        # 基本提示
        prompt = "請將以下英文學術文本翻譯成繁體中文。請注意專業術語的準確性和學術風格：\n\n"
        prompt += text + "\n\n"
        
        # 添加已翻譯術語，確保術語一致性
        consistent_terms = []
        words = re.findall(r'\b\w+\b', text.lower())
        for word in set(words):
            if len(word) > 3 and word in self.term_memory:
                consistent_terms.append((word, self.term_memory[word]))
        
        # 如果有已翻譯術語，添加到提示中
        if consistent_terms:
            prompt += "為確保術語一致性，請在翻譯中使用以下對應關係：\n\n"
            for eng, chi in consistent_terms[:20]:  # 限制數量，避免提示過長
                prompt += f"- {eng} -> {chi}\n"
            prompt += "\n"
        
        # 如果有專業術語資料庫，添加到提示中
        if terminology_db and domain and domain in terminology_db:
            prompt += "翻譯時，請使用以下專業術語對照表（英文 -> 中文）：\n\n"
            
            for term in terminology_db[domain]['terms'][:20]:  # 限制數量，避免提示過長
                english = term['english']
                chinese = term['chinese']
                prompt += f"- {english} -> {chinese}\n"
                
            prompt += "\n請確保使用上述術語的標準翻譯。\n"
        
        # 特殊指示
        prompt += """
請遵循以下翻譯原則：

保持學術風格和專業性
保留原文的段落結構
專有名詞、縮寫和數值保持原樣
翻譯應流暢自然，避免直譯造成的不通順
A, B, C等編號或列表保持原樣
直接輸出翻譯結果，不要加上「翻譯結果：」等前綴
不要使用markdown格式或代碼塊
不要在輸出中加入任何解釋或說明

請直接輸出翻譯結果，不需要任何解釋。
"""
        return prompt

    def _rate_limit(self, max_requests_per_minute: int = 50):
        """限制API調用速率
        
        Args:
            max_requests_per_minute: 每分鐘最大請求數
        """
        self.request_counter += 1
        
        # 檢查是否需要限制
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < 60 and self.request_counter >= max_requests_per_minute:
            # 需要等待的時間
            wait_time = 60 - elapsed
            print(f"達到速率限制，等待 {wait_time:.2f} 秒...")
            time.sleep(wait_time)
            
            # 重置計數器和時間
            self.request_counter = 0
            self.last_request_time = time.time()
        elif elapsed >= 60:
            # 重置計數器和時間
            self.request_counter = 1
            self.last_request_time = current_time

    def get_usage_statistics(self):
        """獲取API使用統計
        
        Returns:
            使用統計數據
        """
        if not self.request_history:
            return {"total_requests": 0}
            
        total_requests = len(self.request_history)
        total_input_chars = sum(req.get("input_length", 0) for req in self.request_history)
        total_output_chars = sum(req.get("output_length", 0) for req in self.request_history)
        
        # 計算每種類型的請求數量
        request_types = {}
        for req in self.request_history:
            req_type = req.get("type", "text")
            request_types[req_type] = request_types.get(req_type, 0) + 1
            
        # 計算每個領域的請求數量
        domains = {}
        for req in self.request_history:
            domain = req.get("domain")
            if domain:
                domains[domain] = domains.get(domain, 0) + 1
        
        return {
            "total_requests": total_requests,
            "total_input_chars": total_input_chars,
            "total_output_chars": total_output_chars,
            "request_types": request_types,
            "domains": domains,
            "terms_in_memory": len(self.term_memory),
            "avg_output_input_ratio": total_output_chars / total_input_chars if total_input_chars > 0 else 0
        }

    def translate_document_section(self, 
                                blocks: List[Dict], 
                                terminology_db: Optional[Dict] = None,
                                domain: Optional[str] = None) -> List[Dict]:
        """翻譯文檔的一個部分（多個連續文本塊）
        
        Args:
            blocks: 文本塊列表
            terminology_db: 專業術語資料庫
            domain: 文檔所屬領域
            
        Returns:
            翻譯後的文本塊列表
        """
        translated_blocks = []
        
        # 將文本塊分組，相似的文本塊合併處理
        grouped_blocks = []
        current_group = []
        current_type = None
        
        for block in blocks:
            block_type = block.get("type", "unknown")
            
            # 如果類型改變或者是圖片/表格/公式，創建新組
            if block_type != current_type or block_type in ["image", "figure", "table", "formula"]:
                if current_group:
                    grouped_blocks.append((current_type, current_group))
                current_group = [block]
                current_type = block_type
            else:
                # 繼續添加到當前組
                current_group.append(block)
        
        # 處理最後一組
        if current_group:
            grouped_blocks.append((current_type, current_group))
        
        # 處理每一組文本塊
        for block_type, group in grouped_blocks:
            if block_type == "text":
                # 合併文本進行翻譯
                text_contents = [block.get("content", "") for block in group]
                combined_text = "\n\n".join(text_contents)
                
                if combined_text.strip():  # 確保有內容需要翻譯
                    translated_text = self.translate_text(combined_text, terminology_db, domain)
                    
                    # 嘗試將翻譯結果分配回各個塊
                    # 如果文本塊之間有明顯的段落界限，使用這些界限分割翻譯結果
                    if len(text_contents) > 1:
                        # 使用較複雜的啟發式方法分割翻譯文本
                        # 基於原文的長度比例分配翻譯文本
                        original_lengths = [len(text) for text in text_contents]
                        total_original_length = sum(original_lengths)
                        total_translated_length = len(translated_text)
                        
                        start_pos = 0
                        for i, block in enumerate(group):
                            # 計算分配比例
                            ratio = original_lengths[i] / total_original_length
                            char_count = int(ratio * total_translated_length)
                            
                            # 分配翻譯文本
                            if i == len(group) - 1:  # 最後一個塊獲取剩餘所有文本
                                block_translated = translated_text[start_pos:]
                            else:
                                # 嘗試找一個更好的斷點（句號、換行等）
                                end_pos = min(start_pos + char_count, len(translated_text))
                                # 向後尋找斷點
                                better_end = translated_text.find('。', end_pos)
                                if better_end == -1 or better_end > end_pos + 20:  # 如果找不到合適的斷點
                                    better_end = translated_text.find('\n', end_pos)
                                if better_end == -1 or better_end > end_pos + 20:
                                    better_end = end_pos
                                
                                block_translated = translated_text[start_pos:better_end+1]
                                start_pos = better_end + 1
                            
                            translated_block = block.copy()
                            translated_block["content_translated"] = block_translated.strip()
                            translated_blocks.append(translated_block)
                    else:
                        # 只有一個塊，直接使用整個翻譯
                        translated_block = group[0].copy()
                        translated_block["content_translated"] = translated_text
                        translated_blocks.append(translated_block)
                else:
                    # 空文本，直接添加原始塊
                    for block in group:
                        translated_blocks.append(block.copy())
            else:
                # 處理非文本塊（圖片、表格、公式等）
                for block in group:
                    translated_block = block.copy()
                    
                    if block_type == "formula":
                        translated_block["content_translated"] = self.translate_formula(block.get("content", ""))
                        if "caption" in block:
                            translated_block["caption_translated"] = self.translate_text(block.get("caption", ""), terminology_db, domain)
                    
                    elif block_type in ["image", "figure"]:
                        if "text_in_image" in block and block["text_in_image"]:
                            translated_block["text_in_image_translated"] = self.translate_image_text(block["text_in_image"])
                        if "caption" in block:
                            translated_block["caption_translated"] = self.translate_text(block.get("caption", ""), terminology_db, domain)
                    
                    elif block_type == "table" and "data" in block:
                        translated_block["data_translated"] = self.translate_table(block["data"])
                        if "caption" in block:
                            translated_block["caption_translated"] = self.translate_text(block.get("caption", ""), terminology_db, domain)
                    
                    translated_blocks.append(translated_block)
        
        return translated_blocks
    
    # 確保_translate_document方法中有處理表格的代碼
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
        if "table_data" in pdf_data:
            for page_idx, page in enumerate(pdf_data["table_data"]):
                if "tables" in page and page["tables"]:
                    for table_idx, table in enumerate(page["tables"]):
                        # 翻譯表格數據
                        if "data" in table:
                            translated_table_data = self.translator.translate_table(table["data"])
                            translated_data["table_data"][page_idx]["tables"][table_idx]["data_translated"] = translated_table_data
                        
                        # 翻譯表格標題
                        if "caption" in table:
                            caption = table["caption"]
                            translated_caption = self.translator.translate_text(caption, terminology_db, domain)
                            translated_data["table_data"][page_idx]["tables"][table_idx]["caption_translated"] = translated_caption
        
        # 處理圖像中的文字
        for img_idx, img_info in enumerate(pdf_data["images"]):
            if "text_in_image" in img_info and img_info["text_in_image"]:
                text_in_image = img_info["text_in_image"]
                translated_text = self.translator.translate_image_text(text_in_image)
                translated_data["images"][img_idx]["text_in_image_translated"] = translated_text
            
            # 翻譯圖片標題
            if "caption" in img_info and img_info["caption"]:
                caption = img_info["caption"]
                translated_caption = self.translator.translate_text(caption, terminology_db, domain)
                translated_data["images"][img_idx]["caption_translated"] = translated_caption
        
        return translated_data