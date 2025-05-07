# 儲存到scripts/translate_special_elements.py
import json
import os
import openai
from config import CONFIG

def translate_math_description(formula, term_mapping):
    # 提取公式中的文字描述部分（通常在 \text{} 中）
    import re
    text_parts = re.findall(r'\\text\{(.*?)\}', formula)
    
    if not text_parts:
        return formula  # 如果沒有文字描述，返回原始公式
    
    # 翻譯每個文字部分
    translated_formula = formula
    for text in text_parts:
        prompt = f"""請將以下數學公式中的文字描述從英文翻譯成繁體中文。不要翻譯數學符號和變量。

原文描述: {text}
繁體中文翻譯:"""
        
        response = openai.ChatCompletion.create(
            model=CONFIG["model"],
            messages=[
                {"role": "system", "content": "你是專業的數學公式翻譯專家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=100
        )
        
        # 替換公式中的文字部分
        translated_text = response.choices[0].message["content"].strip()
        translated_formula = translated_formula.replace(f"\\text{{{text}}}", f"\\text{{{translated_text}}}")
    
    return translated_formula

def translate_table_figure_text(text, element_type, term_mapping):
    prompt = f"""請將以下AI/機器學習論文中的{element_type}描述從英文翻譯成繁體中文。保留任何標號和格式。

以下是一些專業術語及其翻譯，請在翻譯時參考：
"""
    
    # 添加術語對照
    term_list = list(term_mapping.items())
    for i in range(min(10, len(term_list))):
        term, translation = term_list[i]
        prompt += f"- {term} → {translation}\n"
    
    prompt += f"""
原文描述:
{text}

繁體中文翻譯:"""
    
    response = openai.ChatCompletion.create(
        model=CONFIG["model"],
        messages=[
            {"role": "system", "content": f"你是專業的AI/機器學習論文{element_type}翻譯專家。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=500
    )
    
    return response.choices[0].message["content"].strip()

def translate_special_elements(elements_path, term_mapping):
    # 加載特殊元素JSON
    with open(elements_path, 'r', encoding='utf-8') as f:
        special_elements = json.load(f)
    
    # 翻譯公式中的文字部分
    for i, formula_info in enumerate(special_elements["formulas"]):
        print(f"正在處理公式 {i+1}/{len(special_elements['formulas'])}")
        formula = formula_info["formula"]
        special_elements["formulas"][i]["translation"] = translate_math_description(formula, term_mapping)
    
    # 翻譯表格文本
    for i, table_info in enumerate(special_elements["tables"]):
        print(f"正在處理表格 {i+1}/{len(special_elements['tables'])}")
        table_text = table_info["table_text"]
        special_elements["tables"][i]["translation"] = translate_table_figure_text(table_text, "表格", term_mapping)
    
    # 翻譯圖表文本
    for i, figure_info in enumerate(special_elements["figures"]):
        print(f"正在處理圖表 {i+1}/{len(special_elements['figures'])}")
        figure_text = figure_info["figure_text"]
        special_elements["figures"][i]["translation"] = translate_table_figure_text(figure_text, "圖表", term_mapping)
    
    # 保存翻譯後的特殊元素
    output_path = elements_path.replace('.json', '_translated.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(special_elements, f, ensure_ascii=False, indent=2)
    
    return output_path

def translate_all_special_elements():
    # 加載術語對照表
    term_mapping = load_terminology()
    print(f"已加載 {len(term_mapping)} 個術語對照")
    
    # 處理所有特殊元素文件
    for filename in os.listdir(CONFIG["extracted_folder"]):
        if filename.endswith('_special_elements.json'):
            elements_path = os.path.join(CONFIG["extracted_folder"], filename)
            print(f"\n開始處理特殊元素: {filename}")
            output_path = translate_special_elements(elements_path, term_mapping)
            print(f"特殊元素處理完成: {output_path}")

if __name__ == "__main__":
    from translate_text import load_terminology
    translate_all_special_elements()