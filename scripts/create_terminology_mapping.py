# 儲存到scripts/create_terminology_mapping.py
import json
import os
import csv

def create_terminology_csv(terms_json_path, output_csv_path):
    # 加載術語JSON
    with open(terms_json_path, 'r', encoding='utf-8') as f:
        terms = json.load(f)
    
    # 建立CSV文件
    with open(output_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['English Term', 'Chinese Translation', 'Notes'])
        
        # 寫入所有術語，初始時中文翻譯為空
        for term_info in terms:
            writer.writerow([term_info["term"], '', ''])
    
    print(f"已創建術語CSV模板: {output_csv_path}")
    print(f"請手動添加中文翻譯，或使用LLM輔助翻譯")

if __name__ == "__main__":
    create_terminology_csv('terminology/combined_terms.json', 'terminology/terminology_mapping.csv')