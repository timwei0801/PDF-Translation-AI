import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
import csv
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class TerminologyRAG:
    """專業術語檢索增強生成（RAG）系統"""
    
    def __init__(self, embedding_model="paraphrase-multilingual-MiniLM-L12-v2"):
        """初始化專業術語RAG系統
        
        Args:
            embedding_model: 用於生成詞向量的模型名稱
        """
        # 加載詞向量模型（支持多語言）
        self.model = SentenceTransformer(embedding_model)
        
        # 術語資料庫
        self.terminology_db = {
            # "domain": {  # 領域，如"醫學"、"物理學"等
            #     "terms": [  # 術語列表
            #         {
            #             "english": "...",  # 英文術語
            #             "chinese": "...",  # 中文術語
            #             "definition": "...",  # 定義（可選）
            #             "embedding": [...]  # 詞向量
            #         }
            #     ]
            # }
        }
        
        # 向量索引
        self.vector_index = {}
        
    def add_terminology_file(self, file_path: str, domain: str):
        """從文件中添加術語
        
        Args:
            file_path: 術語文件路徑（CSV或JSON）
            domain: 術語所屬領域
        """
        if domain not in self.terminology_db:
            self.terminology_db[domain] = {"terms": []}
            
        if file_path.endswith('.csv'):
            self._add_from_csv(file_path, domain)
        elif file_path.endswith('.json'):
            self._add_from_json(file_path, domain)
        else:
            raise ValueError("不支持的文件格式，僅支持CSV和JSON")
            
        # 更新向量索引
        self._update_vector_index(domain)
        
    def _add_from_csv(self, csv_path: str, domain: str):
        """從CSV文件添加術語"""
        df = pd.read_csv(csv_path)
        
        # 檢查必要的列
        required_cols = ['english', 'chinese']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV文件必須包含以下列: {required_cols}")
        
        for _, row in df.iterrows():
            # 生成英文術語的詞向量
            english_term = row['english']
            embedding = self.model.encode(english_term)
            
            term_entry = {
                'english': english_term,
                'chinese': row['chinese'],
                'embedding': embedding.tolist()
            }
            
            # 添加可選的定義
            if 'definition' in row and not pd.isna(row['definition']):
                term_entry['definition'] = row['definition']
                
            self.terminology_db[domain]['terms'].append(term_entry)
    
    def _add_from_json(self, json_path: str, domain: str):
        """從JSON文件添加術語"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for term in data:
            # 檢查必要的字段
            if 'english' not in term or 'chinese' not in term:
                continue
                
            # 生成英文術語的詞向量
            english_term = term['english']
            embedding = self.model.encode(english_term)
            
            term_entry = {
                'english': english_term,
                'chinese': term['chinese'],
                'embedding': embedding.tolist()
            }
            
            # 添加可選的定義
            if 'definition' in term:
                term_entry['definition'] = term['definition']
                
            self.terminology_db[domain]['terms'].append(term_entry)
    
    def _update_vector_index(self, domain: str):
        """更新指定領域的向量索引"""
        if domain not in self.terminology_db or not self.terminology_db[domain]['terms']:
            return
            
        # 提取該領域所有術語的向量
        vectors = [term['embedding'] for term in self.terminology_db[domain]['terms']]
        self.vector_index[domain] = np.array(vectors)
    
    def add_term(self, english: str, chinese: str, domain: str, definition: Optional[str] = None):
        """添加單個術語
        
        Args:
            english: 英文術語
            chinese: 中文術語
            domain: 所屬領域
            definition: 術語定義（可選）
        """
        if domain not in self.terminology_db:
            self.terminology_db[domain] = {"terms": []}
            
        # 生成詞向量
        embedding = self.model.encode(english)
        
        term_entry = {
            'english': english,
            'chinese': chinese,
            'embedding': embedding.tolist()
        }
        
        if definition:
            term_entry['definition'] = definition
            
        self.terminology_db[domain]['terms'].append(term_entry)
        
        # 更新向量索引
        self._update_vector_index(domain)
    
    def search_term(self, query: str, domain: Optional[str] = None, top_k: int = 5, threshold: float = 0.7) -> List[Dict]:
        """搜索相關術語
        
        Args:
            query: 查詢文本
            domain: 搜索範圍限定的領域（可選）
            top_k: 返回的最大結果數量
            threshold: 相似度閾值
            
        Returns:
            匹配的術語列表，按相似度降序排列
        """
        # 生成查詢向量
        query_vector = self.model.encode(query)
        
        results = []
        
        # 確定搜索的領域範圍
        domains_to_search = [domain] if domain and domain in self.terminology_db else self.terminology_db.keys()
        
        for d in domains_to_search:
            if d not in self.vector_index or len(self.vector_index[d]) == 0:
                continue
                
            # 計算相似度
            similarities = cosine_similarity([query_vector], self.vector_index[d])[0]
            
            # 找出相似度最高的術語
            for i, sim in enumerate(similarities):
                if sim >= threshold:
                    term = self.terminology_db[d]['terms'][i].copy()
                    term['domain'] = d
                    term['similarity'] = float(sim)
                    term.pop('embedding')  # 移除詞向量，避免結果過大
                    results.append(term)
        
        # 按相似度降序排序
        results.sort(key=lambda x: x['similarity'], descending=True)
        
        return results[:top_k]
    
    def lookup_exact_term(self, english_term: str) -> Dict:
        """精確查找術語
        
        Args:
            english_term: 英文術語
            
        Returns:
            找到的術語信息，未找到則返回空字典
        """
        for domain, data in self.terminology_db.items():
            for term in data['terms']:
                if term['english'].lower() == english_term.lower():
                    result = term.copy()
                    result['domain'] = domain
                    result.pop('embedding')
                    return result
                    
        return {}
    
    def extract_terms_from_text(self, text: str, domains: Optional[List[str]] = None) -> List[Dict]:
        """從文本中提取可能的專業術語
        
        Args:
            text: 輸入文本
            domains: 限定的領域列表（可選）
            
        Returns:
            提取的術語列表
        """
        # 簡單的分詞（可以用更複雜的NLP方法改進）
        words = text.split()
        
        # 生成n-gram（1-4個詞的組合）
        ngrams = []
        for n in range(1, 5):
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngrams.append((ngram, i, i+n))
        
        # 查找匹配的術語
        matched_terms = []
        for ngram, start, end in ngrams:
            results = self.search_term(ngram, threshold=0.85)
            if results and (not domains or any(r['domain'] in domains for r in results)):
                for result in results:
                    result['text_span'] = (start, end)
                    result['original_text'] = ngram
                    matched_terms.append(result)
        
        return matched_terms
    
    def save_terminology_db(self, output_path: str):
        """保存術語資料庫到文件
        
        Args:
            output_path: 輸出文件路徑（JSON格式）
        """
        # 創建可序列化的數據結構
        serializable_db = {}
        for domain, data in self.terminology_db.items():
            serializable_db[domain] = {
                "terms": data["terms"]
            }
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_db, f, ensure_ascii=False, indent=2)
    
    def load_terminology_db(self, input_path: str):
        """從文件加載術語資料庫
        
        Args:
            input_path: 輸入文件路徑（JSON格式）
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            self.terminology_db = json.load(f)
            
        # 重建向量索引
        for domain in self.terminology_db:
            self._update_vector_index(domain)
    
    def create_terminology_template(self, output_path: str, format: str = 'csv'):
        """創建術語收集模板
        
        Args:
            output_path: 輸出文件路徑
            format: 輸出格式（'csv'或'json'）
        """
        if format.lower() == 'csv':
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['english', 'chinese', 'definition'])
                # 添加一些示例行
                writer.writerow(['artificial intelligence', '人工智能', '計算機系統模擬人類智能的能力'])
                writer.writerow(['machine learning', '機器學習', ''])
                writer.writerow(['deep learning', '深度學習', ''])
        elif format.lower() == 'json':
            template = [
                {
                    "english": "artificial intelligence",
                    "chinese": "人工智能",
                    "definition": "計算機系統模擬人類智能的能力"
                },
                {
                    "english": "machine learning",
                    "chinese": "機器學習",
                    "definition": ""
                },
                {
                    "english": "deep learning",
                    "chinese": "深度學習",
                    "definition": ""
                }
            ]
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError("不支持的格式，僅支持CSV和JSON")

# 使用示例
if __name__ == "__main__":
    # 創建RAG系統
    rag = TerminologyRAG()
    
    # 創建術語收集模板
    rag.create_terminology_template("terminology_template.csv")
    
    # 添加一些示例術語
    rag.add_term("neural network", "神經網絡", "computer_science", "一種受大腦啟發的機器學習模型")
    rag.add_term("natural language processing", "自然語言處理", "computer_science")
    rag.add_term("transformer model", "變換器模型", "computer_science")
    
    # 搜索術語
    results = rag.search_term("neural networks")
    print("搜索結果:", results)
    
    # 從文本中提取術語
    text = "A neural network is a key technology in natural language processing."
    extracted_terms = rag.extract_terms_from_text(text)
    print("提取的術語:", extracted_terms)
    
    # 保存術語資料庫
    rag.save_terminology_db("terminology_db.json")