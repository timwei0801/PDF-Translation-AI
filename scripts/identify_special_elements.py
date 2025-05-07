# 儲存到scripts/identify_special_elements.py
import json
import re
import os

def identify_math_formulas(text):
    # 識別常見的數學公式形式
    inline_formula = re.findall(r'\$(.*?)\$', text)
    block_formula = re.findall(r'\$\$(.*?)\$\$', text)
    
    # 其他數學公式形式，如 \begin{equation} 等
    other_formula = re.findall(r'\\begin\{(equation|align|matrix).*?\}(.*?)\\end\{\1\}', text, re.DOTALL)
    
    formulas = inline_formula + block_formula + [f[1] for f in other_formula]
    return formulas

def identify_tables(text):
    # 識別表格相關文本
    tables = re.findall(r'(Table \d+[\s\S]*?(?=\n\n|$))', text)
    return tables

def identify_figures(text):
    # 識別圖表相關文本
    figures = re.findall(r'(Fig\.? \d+[\s\S]*?(?=\n\n|$))', text)
    return figures

def identify_special_elements(json_path, output_folder):
    # 加載JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        document = json.load(f)
    
    # 建立特殊元素存儲
    special_elements = {
        "formulas": [],
        "tables": [],
        "figures": []
    }
    
    # 對每個章節處理
    for section in document["sections"]:
        content = section["content"]
        
        # 識別公式
        formulas = identify_math_formulas(content)
        for formula in formulas:
            special_elements["formulas"].append({
                "section": section["title"],
                "formula": formula,
                "translation": ""  # 待翻譯
            })
        
        # 識別表格
        tables = identify_tables(content)
        for table in tables:
            special_elements["tables"].append({
                "section": section["title"],
                "table_text": table,
                "translation": ""  # 待翻譯
            })
        
        # 識別圖表
        figures = identify_figures(content)
        for figure in figures:
            special_elements["figures"].append({
                "section": section["title"],
                "figure_text": figure,
                "translation": ""  # 待翻譯
            })
    
    # 保存特殊元素
    document_name = os.path.basename(json_path).replace('.json', '')
    output_path = f"{output_folder}/{document_name}_special_elements.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(special_elements, f, ensure_ascii=False, indent=2)
    
    return output_path

def process_all_documents(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    processed_files = []
    for filename in os.listdir(input_folder):
        if filename.endswith('.json') and not filename.endswith('_special_elements.json'):
            json_path = os.path.join(input_folder, filename)
            output_path = identify_special_elements(json_path, output_folder)
            processed_files.append(output_path)
    
    return processed_files

if __name__ == "__main__":
    processed_files = process_all_documents('extracted_text', 'extracted_text')
    print(f"已處理 {len(processed_files)} 個檔案的特殊元素")