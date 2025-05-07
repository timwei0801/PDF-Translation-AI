# 儲存到scripts/extract_terminology.py
import json
import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# 下載必要的NLTK資源
nltk.download('punkt')
nltk.download('stopwords')

def extract_terms(json_path, output_folder):
    # 加載JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        document = json.load(f)
    
    # 獲取所有文本
    all_text = ""
    for section in document["sections"]:
        all_text += section["content"] + "\n"
    
    # 標記化文本
    words = word_tokenize(all_text)
    
    # 過濾掉停用詞
    stop_words = set(stopwords.words('english'))
    filtered_words = [w for w in words if not w.lower() in stop_words and w.isalpha()]
    
    # 獲取所有單詞的小寫形式，用於計數
    word_freq = {}
    for word in filtered_words:
        lower_word = word.lower()
        if lower_word in word_freq:
            word_freq[lower_word] += 1
        else:
            word_freq[lower_word] = 1
    
    # 提取雙詞和三詞組
    bi_grams = list(nltk.bigrams(filtered_words))
    tri_grams = list(nltk.trigrams(filtered_words))
    
    # 計算雙詞組頻率
    bigram_freq = {}
    for bigram in bi_grams:
        bigram_str = ' '.join(bigram).lower()
        if bigram_str in bigram_freq:
            bigram_freq[bigram_str] += 1
        else:
            bigram_freq[bigram_str] = 1
    
    # 計算三詞組頻率
    trigram_freq = {}
    for trigram in tri_grams:
        trigram_str = ' '.join(trigram).lower()
        if trigram_str in trigram_freq:
            trigram_freq[trigram_str] += 1
        else:
            trigram_freq[trigram_str] = 1
    
    # 篩選頻率大於1的詞語作為候選術語
    candidate_terms = []
    
    # 添加單詞（頻率大於3）
    for word, freq in word_freq.items():
        if freq > 3 and len(word) > 3:  # 長度大於3的詞
            candidate_terms.append({"term": word, "frequency": freq, "type": "unigram"})
    
    # 添加雙詞組（頻率大於1）
    for bigram, freq in bigram_freq.items():
        if freq > 1:
            candidate_terms.append({"term": bigram, "frequency": freq, "type": "bigram"})
    
    # 添加三詞組（頻率大於1）
    for trigram, freq in trigram_freq.items():
        if freq > 1:
            candidate_terms.append({"term": trigram, "frequency": freq, "type": "trigram"})
    
    # 按頻率排序
    candidate_terms.sort(key=lambda x: x["frequency"], reverse=True)
    
    # 保存術語
    document_name = os.path.basename(json_path).replace('.json', '')
    output_path = f"{output_folder}/{document_name}_terms.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(candidate_terms, f, ensure_ascii=False, indent=2)
    
    return output_path, candidate_terms[:100]  # 返回前100個術語

def process_all_documents_for_terms(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    all_terms = []
    for filename in os.listdir(input_folder):
        if filename.endswith('.json') and not filename.endswith('_special_elements.json') and not filename.endswith('_terms.json'):
            json_path = os.path.join(input_folder, filename)
            output_path, terms = extract_terms(json_path, output_folder)
            all_terms.extend(terms)
    
    # 合併所有文檔的術語並去重
    term_dict = {}
    for term_info in all_terms:
        term = term_info["term"]
        if term in term_dict:
            term_dict[term]["frequency"] += term_info["frequency"]
        else:
            term_dict[term] = term_info
    
    # 重新排序
    combined_terms = list(term_dict.values())
    combined_terms.sort(key=lambda x: x["frequency"], reverse=True)
    
    # 保存合併後的術語表
    combined_output_path = f"{output_folder}/combined_terms.json"
    with open(combined_output_path, 'w', encoding='utf-8') as f:
        json.dump(combined_terms, f, ensure_ascii=False, indent=2)
    
    return combined_output_path

if __name__ == "__main__":
    combined_terms_path = process_all_documents_for_terms('extracted_text', 'terminology')
    print(f"已生成合併術語表: {combined_terms_path}")