# 儲存到scripts/run_pipeline.py
import os
import subprocess
import time

def run_process(script_name, description):
    print(f"\n{'=' * 50}")
    print(f"步驟: {description}")
    print(f"{'=' * 50}\n")
    
    start_time = time.time()
    subprocess.run(['python', f'scripts/{script_name}'])
    end_time = time.time()
    
    print(f"\n完成時間: {end_time - start_time:.2f} 秒")

def main():
    # 確保所有必要的文件夾存在
    for folder in ['raw_pdfs', 'extracted_text', 'translations', 'terminology', 'final_reports']:
        os.makedirs(folder, exist_ok=True)
    
    # 檢查是否已放置PDF
    pdf_count = len([f for f in os.listdir('raw_pdfs') if f.endswith('.pdf')])
    if pdf_count == 0:
        print("請先將PDF文件放入 'raw_pdfs' 文件夾，然後再運行此腳本")
        return
    
    print(f"找到 {pdf_count} 個PDF文件，開始處理...")
    
    # 執行管道
    run_process('extract_text.py', '提取PDF文本並保留結構')
    run_process('identify_special_elements.py', '識別數學公式和特殊元素')
    run_process('extract_terminology.py', '從論文中提取關鍵術語')
    
    # 等待用戶填寫術語對照表
    if not os.path.exists('terminology/terminology_mapping.csv'):
        run_process('create_terminology_mapping.py', '創建術語映射模板')
        print("\n請填寫 'terminology/terminology_mapping.csv' 中的術語翻譯")
        print("完成後按Enter鍵繼續...")
        input()
    
    # 繼續翻譯流程
    run_process('translate_text.py', '使用術語庫和RAG進行初步翻譯')
    run_process('translate_special_elements.py', '處理數學公式、表格和圖表')
    run_process('generate_final_report.py', '組合生成最終翻譯報告')
    
    print("\n翻譯流程完成!")
    print(f"最終報告已生成在 'final_reports' 文件夾中")

if __name__ == "__main__":
    main()