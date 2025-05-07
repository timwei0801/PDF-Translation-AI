# 儲存到scripts/translate_text.py
import json
import os
import csv
import openai
from config import CONFIG

def load_terminology():
    term_mapping = {}
    if os.path.exists(CONFIG["terminology_path"]):
        with open(CONFIG["terminology_path"], 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # 跳過標題行
            next(reader)
            for row in reader:
                if len(row) >= 2 and row[1].strip():  # 如果有中文翻譯
                    term_mapping[row[0].lower()] = row[1]
    return term_mapping

def translate_section_with_rag(section_title, section_content, term_mapping):
    # 預處理內容，標記專業術語
    processed_content = section_content
    for term, translation in term_mapping.items():
        processed_content = processed_content.replace(f" {term} ", f" [{term}] ")
    
    # 準備提示
    prompt = f"""請將以下AI/機器學習領域的英文文本翻譯成繁體中文。

文本標題：{section_title}

以下是一些專業術語及其翻譯，請在翻譯時參考：
"""
    
    # 添加術語對照
    term_list = list(term_mapping.items())
    for i in range(min(15, len(term_list))):
        term, translation = term_list[i]
        prompt += f"- {term} → {translation}\n"
    
    prompt += """
翻譯規則：
1. 保持學術嚴謹性和專業性
2. 專業術語使用對應的標準中文翻譯
3. 數學公式和變量保持不變
4. 保留原文段落結構
5. 使用繁體中文

待翻譯文本：
"""
    prompt += processed_content
    
    # 調用Claude API進行翻譯
    response = client.messages.create(
        model=CONFIG["model"],
        max_tokens=CONFIG["max_tokens"],
        temperature=CONFIG["temperature"],
        system="你是專業的AI/機器學習論文翻譯專家。",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # 提取翻譯結果
    translation = response.content[0].text
    return translation

def translate_document(document_path, output_folder, term_mapping):
    # 加載JSON文件
    with open(document_path, 'r', encoding='utf-8') as f:
        document = json.load(f)
    
    # 新文檔用於保存翻譯
    translated_document = {
        "title": document["title"],
        "sections": []
    }
    
    # 翻譯每個章節
    for section in document["sections"]:
        print(f"正在翻譯章節: {section['title']}")
        translated_content = translate_section_with_rag(
            section["title"], 
            section["content"], 
            term_mapping
        )
        
        translated_section = {
            "title": section["title"],
            "content": section["content"],
            "translated_content": translated_content,
            "page_range": section["page_range"]
        }
        
        translated_document["sections"].append(translated_section)
    
    # 保存翻譯後的文檔
    os.makedirs(output_folder, exist_ok=True)
    document_name = os.path.basename(document_path).replace('.json', '')
    output_path = f"{output_folder}/{document_name}_translated.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(translated_document, f, ensure_ascii=False, indent=2)
    
    return output_path

def translate_all_documents():
    # 加載術語對照表
    term_mapping = load_terminology()
    print(f"已加載 {len(term_mapping)} 個術語對照")
    
    # 創建翻譯輸出文件夾
    os.makedirs(CONFIG["translation_folder"], exist_ok=True)
    
    # 處理所有文檔
    for filename in os.listdir(CONFIG["extracted_folder"]):
        if filename.endswith('.json') and not filename.endswith('_special_elements.json') and not filename.endswith('_terms.json'):
            document_path = os.path.join(CONFIG["extracted_folder"], filename)
            print(f"\n開始翻譯文檔: {filename}")
            output_path = translate_document(
                document_path, 
                CONFIG["translation_folder"], 
                term_mapping
            )
            print(f"文檔翻譯完成: {output_path}")

if __name__ == "__main__":
    translate_all_documents()