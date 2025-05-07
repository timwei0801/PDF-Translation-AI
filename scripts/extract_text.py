# 儲存到scripts/extract_text.py
import PyPDF2
import os
import re
import json

def extract_text_with_structure(pdf_path, output_folder):
    document_name = os.path.basename(pdf_path).replace('.pdf', '')
    output_path = f"{output_folder}/{document_name}.json"
    
    # 開啟PDF
    pdf_reader = PyPDF2.PdfReader(pdf_path)
    total_pages = len(pdf_reader.pages)
    
    # 建立結構化文件
    document = {
        "title": document_name,
        "pages": [],
        "sections": []
    }
    
    current_section = {"title": "", "content": "", "page_range": []}
    
    for i in range(total_pages):
        page = pdf_reader.pages[i]
        text = page.extract_text()
        
        # 儲存頁面文本
        document["pages"].append({
            "page_number": i + 1,
            "text": text
        })
        
        # 檢測標題（這裡使用簡單的啟發式方法）
        lines = text.split('\n')
        for line in lines:
            # 檢測可能的標題（全大寫或數字開頭）
            if line.strip().isupper() or re.match(r'^[I\d]+\.?\s+[A-Z]', line.strip()):
                if current_section["title"]:
                    # 儲存當前章節並開始新章節
                    document["sections"].append(current_section)
                    current_section = {"title": line.strip(), "content": "", "page_range": [i + 1]}
                else:
                    current_section["title"] = line.strip()
                    current_section["page_range"] = [i + 1]
            else:
                # 添加到當前章節內容
                current_section["content"] += line + "\n"
                if i + 1 not in current_section["page_range"]:
                    current_section["page_range"].append(i + 1)
    
    # 添加最後一個章節
    if current_section["title"]:
        document["sections"].append(current_section)
    
    # 保存為JSON文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
    
    return output_path

# 處理所有PDF
def process_all_pdfs(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    processed_files = []
    for filename in os.listdir(input_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(input_folder, filename)
            output_path = extract_text_with_structure(pdf_path, output_folder)
            processed_files.append(output_path)
    
    return processed_files

# 執行提取
if __name__ == "__main__":
    processed_files = process_all_pdfs('raw_pdfs', 'extracted_text')
    print(f"已處理 {len(processed_files)} 個檔案")