# 儲存到scripts/generate_final_report.py
import json
import os
from config import CONFIG

def merge_translations(translated_doc_path, special_elements_path, output_folder):
    # 加載已翻譯的文檔
    with open(translated_doc_path, 'r', encoding='utf-8') as f:
        translated_doc = json.load(f)
    
    # 加載已翻譯的特殊元素
    special_elements_translated_path = special_elements_path.replace('.json', '_translated.json')
    if os.path.exists(special_elements_translated_path):
        with open(special_elements_translated_path, 'r', encoding='utf-8') as f:
            special_elements = json.load(f)
    else:
        special_elements = {"formulas": [], "tables": [], "figures": []}
    
    # 準備最終報告內容
    document_name = os.path.basename(translated_doc_path).replace('_translated.json', '')
    report_content = f"# {document_name} 翻譯報告\n\n"
    
    # 添加每個章節
    for section in translated_doc["sections"]:
        report_content += f"## {section['title']}\n\n"
        report_content += "### 原文\n\n"
        report_content += section["content"] + "\n\n"
        report_content += "### 翻譯\n\n"
        report_content += section["translated_content"] + "\n\n"
    
    # 添加特殊元素的翻譯
    if special_elements["formulas"]:
        report_content += "## 數學公式翻譯\n\n"
        for formula_info in special_elements["formulas"]:
            report_content += f"- 原公式: {formula_info['formula']}\n"
            report_content += f"- 翻譯後: {formula_info['translation']}\n\n"
    
    if special_elements["tables"]:
        report_content += "## 表格翻譯\n\n"
        for table_info in special_elements["tables"]:
            report_content += f"### 所在章節: {table_info['section']}\n\n"
            report_content += f"**原文:**\n\n{table_info['table_text']}\n\n"
            report_content += f"**翻譯:**\n\n{table_info['translation']}\n\n"
    
    if special_elements["figures"]:
        report_content += "## 圖表翻譯\n\n"
        for figure_info in special_elements["figures"]:
            report_content += f"### 所在章節: {figure_info['section']}\n\n"
            report_content += f"**原文:**\n\n{figure_info['figure_text']}\n\n"
            report_content += f"**翻譯:**\n\n{figure_info['translation']}\n\n"
    
    # 保存最終報告
    os.makedirs(output_folder, exist_ok=True)
    output_path = f"{output_folder}/{document_name}_final_report.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    return output_path

def generate_all_reports():
    # 創建報告輸出文件夾
    output_folder = "final_reports"
    os.makedirs(output_folder, exist_ok=True)
    
    # 獲取所有已翻譯的文檔
    for filename in os.listdir(CONFIG["translation_folder"]):
        if filename.endswith('_translated.json'):
            translated_doc_path = os.path.join(CONFIG["translation_folder"], filename)
            document_name = filename.replace('_translated.json', '')
            
            # 尋找對應的特殊元素文件
            special_elements_path = os.path.join(CONFIG["extracted_folder"], f"{document_name}_special_elements.json")
            
            if os.path.exists(special_elements_path):
                print(f"\n生成報告: {document_name}")
                output_path = merge_translations(translated_doc_path, special_elements_path, output_folder)
                print(f"報告已生成: {output_path}")
            else:
                print(f"警告: 找不到文檔 {document_name} 的特殊元素文件")

if __name__ == "__main__":
    generate_all_reports()