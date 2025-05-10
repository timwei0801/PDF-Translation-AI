import os
import json
import time
import anthropic
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
            
            # 記錄請求
            self.request_history.append({
                "timestamp": time.time(),
                "input_length": len(text),
                "output_length": len(translated_text),
                "domain": domain,
                "model": self.model
            })
            
            return translated_text
            
        except Exception as e:
            print(f"翻譯時出錯: {str(e)}")
            return ""
    
    def translate_formula(self, formula: str) -> str:
        """翻譯數學公式（保留公式結構，僅翻譯文字部分）
        
        Args:
            formula: 包含數學公式的文本
            
        Returns:
            翻譯後的公式
        """
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

```
{formula}
```

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
            
            # 去除可能的```標記
            translated_formula = translated_formula.replace("```", "").strip()
            
            # 記錄請求
            self.request_history.append({
                "timestamp": time.time(),
                "input_length": len(formula),
                "output_length": len(translated_formula),
                "type": "formula",
                "model": self.model
            })
            
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
            
            # 記錄請求
            self.request_history.append({
                "timestamp": time.time(),
                "input_length": len(text_in_image),
                "output_length": len(translated_text),
                "type": "image_text",
                "model": self.model
            })
            
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
        # 限制API調用速率
        self._rate_limit()
        
        # 將表格轉換為JSON字符串
        table_json = json.dumps(table_data, ensure_ascii=False)
        
        # 創建專門用於表格翻譯的提示
        prompt = f"""
請將以下JSON格式的表格數據從英文翻譯成繁體中文。表格結構是一個二維陣列，每個元素是單元格的文本內容：

```json
{table_json}
```

請直接輸出翻譯後的JSON格式表格數據，保持原始結構不變，只翻譯文本內容。不要翻譯專有名詞、縮寫和數值。不需要任何解釋，只需要輸出翻譯後的JSON。
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
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = result_text.strip()
            
            # 解析JSON
            try:
                translated_table = json.loads(json_str)
                
                # 記錄請求
                self.request_history.append({
                    "timestamp": time.time(),
                    "input_cells": sum(len(row) for row in table_data),
                    "output_cells": sum(len(row) for row in translated_table),
                    "type": "table",
                    "model": self.model
                })
                
                return translated_table
            except json.JSONDecodeError:
                print("無法解析翻譯後的表格JSON")
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
1. 保持學術風格和專業性
2. 保留原文的段落結構
3. 專有名詞、縮寫和數值保持原樣
4. 翻譯應流暢自然，避免直譯造成的不通順
5. A, B, C等編號或列表保持原樣

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
        
        # 將連續的文本塊合併處理，以減少API呼叫
        text_buffer = []
        current_blocks = []
        
        for block in blocks:
            if block["type"] == "text":
                text_buffer.append(block["content"])
                current_blocks.append(block)
            else:
                # 處理之前累積的文本
                if text_buffer:
                    translated_text = self.translate_text(
                        "\n\n".join(text_buffer), 
                        terminology_db, 
                        domain
                    )
                    
                    # 嘗試將翻譯結果分配回各個塊
                    translated_paragraphs = translated_text.split("\n\n")
                    
                    # 如果段落數量不匹配，簡單地按比例分配
                    if len(translated_paragraphs) != len(text_buffer):
                        for i, original_block in enumerate(current_blocks):
                            ratio = len(original_block["content"]) / sum(len(tb) for tb in text_buffer)
                            start = int(ratio * i * len(translated_text))
                            end = int(ratio * (i + 1) * len(translated_text))
                            translated_block = original_block.copy()
                            translated_block["content_translated"] = translated_text[start:end]
                            translated_blocks.append(translated_block)
                    else:
                        # 段落數量匹配，直接一一對應
                        for i, original_block in enumerate(current_blocks):
                            translated_block = original_block.copy()
                            translated_block["content_translated"] = translated_paragraphs[i]
                            translated_blocks.append(translated_block)
                    
                    # 清空緩衝區
                    text_buffer = []
                    current_blocks = []
                
                # 處理非文本塊
                translated_block = block.copy()
                
                if block["type"] == "formula":
                    translated_block["content_translated"] = self.translate_formula(block["content"])
                elif block["type"] == "image" and "text_in_image" in block:
                    if block["text_in_image"]:
                        translated_block["text_in_image_translated"] = self.translate_image_text(block["text_in_image"])
                elif block["type"] == "table" and "data" in block:
                    translated_block["data_translated"] = self.translate_table(block["data"])
                
                translated_blocks.append(translated_block)
        
        # 處理剩餘的文本
        if text_buffer:
            translated_text = self.translate_text(
                "\n\n".join(text_buffer), 
                terminology_db, 
                domain
            )
            
            # 嘗試將翻譯結果分配回各個塊
            translated_paragraphs = translated_text.split("\n\n")
            
            # 如果段落數量不匹配，簡單地按比例分配
            if len(translated_paragraphs) != len(text_buffer):
                for i, original_block in enumerate(current_blocks):
                    ratio = len(original_block["content"]) / sum(len(tb) for tb in text_buffer)
                    start = int(ratio * i * len(translated_text))
                    end = int(ratio * (i + 1) * len(translated_text))
                    translated_block = original_block.copy()
                    translated_block["content_translated"] = translated_text[start:end]
                    translated_blocks.append(translated_block)
            else:
                # 段落數量匹配，直接一一對應
                for i, original_block in enumerate(current_blocks):
                    translated_block = original_block.copy()
                    translated_block["content_translated"] = translated_paragraphs[i]
                    translated_blocks.append(translated_block)
        
        return translated_blocks

# 使用示例
if __name__ == "__main__":
    # 初始化翻譯器
    translator = ClaudeTranslator()
    
    # 翻譯普通文本
    english_text = "The transformer architecture has revolutionized natural language processing by enabling more efficient parallel training and better modeling of long-range dependencies."
    chinese_text = translator.translate_text(english_text, domain="computer_science")
    print(f"原文: {english_text}")
    print(f"翻譯: {chinese_text}")
    
    # 翻譯數學公式
    formula = "Let X = {x_1, x_2, ..., x_n} be a set of data points where each x_i ∈ ℝ^d, and let f(x) be a function that maps each data point to a scalar value."
    formula_translated = translator.translate_formula(formula)
    print(f"原公式: {formula}")
    print(f"翻譯後: {formula_translated}")
    
    # 查看使用統計
    stats = translator.get_usage_statistics()
    print(f"API使用統計: {stats}")