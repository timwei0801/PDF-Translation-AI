#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
創建一個可切換顯示原文/翻譯的 HTML 頁面
保持原文的排版，方便對照圖表等元素
特別處理圖片、公式和表格的顯示
"""

import os
import json
import argparse
import shutil
import glob

def find_matching_image(base_dir, image_path):
    """尋找匹配的圖片文件，支持多種路徑格式"""
    # 直接路徑檢查
    if not image_path:
        return None
    
    full_path = os.path.join(base_dir, image_path)
    if os.path.exists(full_path):
        return image_path
    
    # 嘗試不同的目錄結構
    filename = os.path.basename(image_path)
    possible_paths = [
        os.path.join("images", filename),
        os.path.join("translated_pdfs", "images", filename),
        filename
    ]
    
    for path in possible_paths:
        full_path = os.path.join(base_dir, path)
        if os.path.exists(full_path):
            return path
    
    # 最後嘗試只根據前綴匹配
    if '_page' in filename and '_img' in filename:
        prefix = filename.split('_page')[0]
        page_part = filename.split('_page')[1].split('_img')[0]
        img_part = filename.split('_img')[1].split('.')[0]
        
        # 在整個目錄中查找匹配的圖片
        for img_file in glob.glob(os.path.join(base_dir, "**", "*.png"), recursive=True):
            if prefix in img_file and f"page{page_part}" in img_file and f"img{img_part}" in img_file:
                return os.path.relpath(img_file, base_dir)
    
    return None

def create_toggle_html(json_path, output_path=None, copy_images=True):
    """創建可切換原文/翻譯的 HTML
    
    Args:
        json_path: 翻譯數據 JSON 文件路徑
        output_path: 輸出 HTML 文件路徑
        copy_images: 是否複製圖片到輸出目錄
    """
    # 讀取 JSON 文件
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"讀取 JSON 文件時出錯: {e}")
        return None
    
    # 設置默認輸出路徑
    if not output_path:
        base_dir = os.path.dirname(json_path)
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        output_path = os.path.join(base_dir, f"toggle_{base_name}.html")
    
    # 獲取HTML輸出目錄
    output_dir = os.path.dirname(output_path)
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 圖片處理 - 創建目標圖片目錄
    images_dir = os.path.join(output_dir, "output_images")
    os.makedirs(images_dir, exist_ok=True)
    
    # 獲取 JSON 文件所在的基礎目錄
    source_base_dir = os.path.dirname(json_path)
    
    # 先掃描所有可用的圖片
    available_images = []
    for root, _, files in os.walk(source_base_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                rel_path = os.path.relpath(os.path.join(root, file), source_base_dir)
                available_images.append(rel_path)
    
    print(f"找到 {len(available_images)} 個可用圖片文件")
    
    # 更新JSON中的圖片路徑，指向新位置
    if copy_images:
        # 從JSON中尋找並複製所有圖片
        copied_images = []
        
        # 處理text_data中的圖片
        for page_idx, page in enumerate(data.get("text_data", [])):
            for block_idx, block in enumerate(page.get("blocks", [])):
                if block.get("type") in ["image", "figure"]:
                    # 獲取或設置圖片路徑
                    image_path = block.get("image_path", "")
                    
                    # 如果路徑為空，嘗試設置一個默認路徑
                    if not image_path:
                        basename = os.path.splitext(os.path.basename(json_path))[0]
                        default_image_name = f"{basename}_page{page_idx+1}_img{block_idx+1}.png"
                        
                        # 嘗試在可用圖片中查找匹配的文件
                        for img in available_images:
                            if default_image_name in img:
                                image_path = img
                                block["image_path"] = image_path
                                print(f"為空路徑找到匹配圖片: {image_path}")
                                break
                    else:
                        # 嘗試修正現有路徑
                        matched_path = find_matching_image(source_base_dir, image_path)
                        if matched_path and matched_path != image_path:
                            image_path = matched_path
                            block["image_path"] = matched_path
                            print(f"修正圖片路徑: {image_path} -> {matched_path}")
                    
                    if not image_path:
                        print(f"警告: 頁面 {page_idx+1} 的塊 {block_idx} 未找到有效圖片路徑")
                        continue
                    
                    # 源圖片路徑
                    src_path = os.path.join(source_base_dir, image_path)
                    
                    # 獲取圖片文件名
                    image_filename = os.path.basename(image_path)
                    
                    # 新的目標路徑
                    dst_path = os.path.join(images_dir, image_filename)
                    
                    # 更新JSON中的圖片路徑
                    relative_dst_path = os.path.join("output_images", image_filename)
                    block["image_path"] = relative_dst_path
                    
                    # 確保目標目錄存在
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # 複製圖片
                    if os.path.exists(src_path):
                        try:
                            # 檢查是否需要複製（避免源和目標相同）
                            if os.path.normpath(src_path) != os.path.normpath(dst_path):
                                shutil.copy2(src_path, dst_path)
                                copied_images.append(src_path)
                                print(f"已複製圖片: {src_path} -> {dst_path}")
                        except Exception as e:
                            print(f"複製圖片時出錯: {e}")
                    else:
                        print(f"圖片源文件不存在: {src_path}")
        
        # 處理images中的圖片
        for img_info in data.get("images", []):
            if "image_path" in img_info:
                # 獲取或設置圖片路徑
                image_path = img_info.get("image_path", "")
                
                # 如果路徑為空，繼續下一個
                if not image_path:
                    continue
                
                # 嘗試修正現有路徑
                matched_path = find_matching_image(source_base_dir, image_path)
                if matched_path and matched_path != image_path:
                    image_path = matched_path
                    img_info["image_path"] = matched_path
                    print(f"修正圖片路徑: {image_path} -> {matched_path}")
                
                # 源圖片路徑
                src_path = os.path.join(source_base_dir, image_path)
                
                # 獲取圖片文件名
                image_filename = os.path.basename(image_path)
                
                # 新的目標路徑
                dst_path = os.path.join(images_dir, image_filename)
                
                # 更新JSON中的圖片路徑
                relative_dst_path = os.path.join("output_images", image_filename)
                img_info["image_path"] = relative_dst_path
                
                # 確保目標目錄存在
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # 複製圖片
                if os.path.exists(src_path):
                    try:
                        # 檢查是否需要複製（避免源和目標相同）
                        if os.path.normpath(src_path) != os.path.normpath(dst_path):
                            shutil.copy2(src_path, dst_path)
                            copied_images.append(src_path)
                            print(f"已複製圖片: {src_path} -> {dst_path}")
                    except Exception as e:
                        print(f"複製圖片時出錯: {e}")
                else:
                    print(f"圖片源文件不存在: {src_path}")
    
    # 創建 HTML 內容
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>原文/翻譯切換查看</title>
    <!-- MathJax 支持 -->
    <script type="text/javascript" id="MathJax-script" async
      src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
    </script>
    <script>
      window.MathJax = {
        tex: {
          inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
          displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
        }
      };
    </script>
    <style>
        body {
            font-family: Arial, "Microsoft YaHei", sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 15px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .toggle-container {
            display: flex;
            justify-content: center;
            margin: 10px 0;
        }
        .toggle-btn {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 0 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        .toggle-btn:hover {
            background-color: #2980b9;
        }
        .toggle-btn.active {
            background-color: #2980b9;
            font-weight: bold;
        }
        .page-container {
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .page-header {
            background-color: #f0f0f0;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 5px;
            font-weight: bold;
            color: #333;
        }
        .block {
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 5px;
            position: relative;
        }
        .original {
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
        }
        .translated {
            background-color: #f0fff0;
            border-left: 4px solid #27ae60;
            display: none;
        }
        .formula {
            font-family: "Courier New", monospace;
            background-color: #f9f9f9;
            padding: 10px;
            overflow-x: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .formula-caption {
            margin-top: 10px;
            font-style: italic;
            color: #666;
        }
        .figure {
            text-align: center;
            padding: 10px;
            margin: 15px 0;
            background-color: #f9f9f9;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .figure img {
            max-width: 100%;
            height: auto;
            margin: 10px 0;
        }
        .figure-caption {
            margin-top: 10px;
            font-style: italic;
            color: #555;
        }
        .table-container {
            overflow-x: auto;
            margin: 15px 0;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #ddd;
        }
        .table th, .table td {
            padding: 8px;
            border: 1px solid #ddd;
            text-align: left;
        }
        .table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .shared-element {
            display: block;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        .page-nav {
            position: fixed;
            top: 80px;
            right: 20px;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            max-height: 80vh;
            overflow-y: auto;
        }
        .page-nav-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .page-nav a {
            display: block;
            margin: 5px 0;
            color: #3498db;
            text-decoration: none;
        }
        .page-nav a:hover {
            text-decoration: underline;
        }
        .placeholder-image {
            width: 80%;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f0f0;
            border: 1px dashed #aaa;
            text-align: center;
            color: #666;
        }
        @media print {
            .header, .page-nav, .toggle-container {
                display: none;
            }
            .translated {
                display: block !important;
            }
            .original {
                display: none !important;
            }
            .shared-element {
                display: block !important;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>原文/翻譯切換查看</h1>
        <div class="toggle-container">
            <button class="toggle-btn active" onclick="toggleView('original')">顯示原文</button>
            <button class="toggle-btn" onclick="toggleView('translated')">顯示翻譯</button>
            <button class="toggle-btn" onclick="toggleView('both')">顯示雙語對照</button>
            <button class="toggle-btn" onclick="window.print()">列印翻譯版本</button>
        </div>
    </div>
    
    <div class="container">
        <div class="page-nav">
            <div class="page-nav-title">頁面導航</div>
"""
    
    # 添加頁面導航
    for page_idx in range(len(data.get("text_data", []))):
        html += '            <a href="#page-{0}">第 {0} 頁</a>\n'.format(page_idx+1)
    
    html += """        </div>
    
"""
    
    # 添加每一頁的內容
    for page_idx, page in enumerate(data.get("text_data", [])):
        html += '        <div class="page-container" id="page-{0}">\n'.format(page_idx+1)
        html += '            <div class="page-header">第 {0} 頁</div>\n'.format(page_idx+1)
        
        for block_idx, block in enumerate(page.get("blocks", [])):
            block_id = f"block-{page_idx}-{block_idx}"
            
            # 根據不同的內容類型處理
            if block.get("type") == "text":
                # 原文區塊
                html += '            <div id="{0}-original" class="block original">\n'.format(block_id)
                content = block.get("content", "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                html += '                <p>{0}</p>\n'.format(content)
                html += '            </div>\n'
                
                # 翻譯區塊
                if "content_translated" in block:
                    html += '            <div id="{0}-translated" class="block translated">\n'.format(block_id)
                    translated = block.get("content_translated", "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                    html += '                <p>{0}</p>\n'.format(translated)
                    html += '            </div>\n'
            
            elif block.get("type") == "formula":
                # 處理公式 - 在雙語模式下只顯示一次
                html += '            <div id="{0}-shared" class="block shared-element formula">\n'.format(block_id)
                formula = block.get("content", "").replace("<", "&lt;").replace(">", "&gt;")
                
                # 處理公式，支援 TeX 數學公式
                if not formula.startswith('$') and not formula.endswith('$') and not formula.startswith('\\(') and not formula.endswith('\\)'):
                    if '\n' in formula or len(formula) > 50:  # 較長公式使用顯示模式
                        formula = f"$${formula}$$"
                    else:  # 較短公式使用內聯模式
                        formula = f"${formula}$"
                
                html += f'                <div>{formula}</div>\n'
                
                # 如果有公式標題或說明
                if "caption" in block:
                    html += '                <div class="formula-caption original">{0}</div>\n'.format(block.get("caption", ""))
                    
                # 如果有翻譯版本的公式描述
                if "caption_translated" in block:
                    html += '                <div class="formula-caption translated" style="display:none;">{0}</div>\n'.format(block.get("caption_translated", ""))
                
                html += '            </div>\n'
            
            elif block.get("type") in ["figure", "image"]:
                # 處理圖片 - 在雙語模式下只顯示一次
                html += '            <div id="{0}-shared" class="block shared-element figure">\n'.format(block_id)
                
                # 查找圖片路徑
                image_path = block.get("image_path", "")
                
                # 檢查圖片文件是否存在
                local_image_path = os.path.join(output_dir, image_path) if image_path else ""
                
                if image_path and os.path.exists(local_image_path):
                    # 圖片存在，顯示圖片
                    html += '                <img src="{0}" alt="{1}">\n'.format(image_path, block.get("caption", "圖片"))
                    
                    # 圖片標題 - 原文
                    if "caption" in block:
                        html += '                <div class="figure-caption original">{0}</div>\n'.format(block.get("caption", ""))
                    
                    # 圖片標題 - 翻譯
                    if "caption_translated" in block:
                        html += '                <div class="figure-caption translated" style="display:none;">{0}</div>\n'.format(block.get("caption_translated", ""))
                else:
                    # 圖片不存在，顯示預設圖片或錯誤信息
                    html += '                <div class="placeholder-image">\n'
                    html += '                    <p>圖片無法顯示</p>\n'
                    if image_path:
                        html += f'                    <p>路徑: {image_path}</p>\n'
                    if "caption" in block:
                        html += f'                    <p>標題: {block.get("caption", "")}</p>\n'
                    html += '                </div>\n'
                    
                    # 圖片標題 - 原文
                    if "caption" in block:
                        html += '                <div class="figure-caption original">{0}</div>\n'.format(block.get("caption", ""))
                    
                    # 圖片標題 - 翻譯
                    if "caption_translated" in block:
                        html += '                <div class="figure-caption translated" style="display:none;">{0}</div>\n'.format(block.get("caption_translated", ""))
                
                html += '            </div>\n'
                
            elif block.get("type") == "table":
                # 處理表格 - 在雙語模式下只顯示一次
                html += '            <div id="{0}-shared" class="block shared-element table-container">\n'.format(block_id)
                
                # 表格標題 - 原文
                if "caption" in block:
                    html += '                <div class="table-caption original">{0}</div>\n'.format(block.get("caption", ""))
                
                # 表格標題 - 翻譯
                if "caption_translated" in block:
                    html += '                <div class="table-caption translated" style="display:none;">{0}</div>\n'.format(block.get("caption_translated", ""))
                
                # 表格內容
                if "content" in block:
                    html += '                {0}\n'.format(block["content"])
                elif "data" in block:
                    # 創建HTML表格
                    html += '                <table class="table">\n'
                    
                    # 如果有表頭，先處理表頭
                    if block.get("has_header", False) and len(block["data"]) > 0:
                        html += '                    <thead>\n'
                        html += '                        <tr>\n'
                        for cell in block["data"][0]:
                            html += '                            <th>{0}</th>\n'.format(cell)
                        html += '                        </tr>\n'
                        html += '                    </thead>\n'
                        start_row = 1
                    else:
                        start_row = 0
                    
                    # 處理表格主體
                    html += '                    <tbody>\n'
                    for row in block["data"][start_row:]:
                        html += '                        <tr>\n'
                        for cell in row:
                            html += '                            <td>{0}</td>\n'.format(cell)
                        html += '                        </tr>\n'
                    html += '                    </tbody>\n'
                    html += '                </table>\n'
                else:
                    html += '                <div style="text-align: center; padding: 20px; background-color: #f0f0f0; color: #666;">表格無法顯示</div>\n'
                
                html += '            </div>\n'
        
        html += '        </div>\n'
    
    html += """    </div>

    <script>
        function toggleView(mode) {
            const originalBlocks = document.querySelectorAll('.original');
            const translatedBlocks = document.querySelectorAll('.translated');
            const buttons = document.querySelectorAll('.toggle-btn');
            
            // 重置所有按鈕樣式
            buttons.forEach(btn => btn.classList.remove('active'));
            
            if (mode === 'original') {
                // 顯示原文，隱藏翻譯
                originalBlocks.forEach(block => {
                    block.style.display = 'block';
                });
                translatedBlocks.forEach(block => {
                    block.style.display = 'none';
                });
                document.querySelector('.toggle-btn:nth-child(1)').classList.add('active');
            } else if (mode === 'translated') {
                // 顯示翻譯，隱藏原文
                originalBlocks.forEach(block => {
                    block.style.display = 'none';
                });
                translatedBlocks.forEach(block => {
                    block.style.display = 'block';
                });
                document.querySelector('.toggle-btn:nth-child(2)').classList.add('active');
            } else if (mode === 'both') {
                // 顯示雙語對照
                originalBlocks.forEach(block => {
                    block.style.display = 'block';
                });
                translatedBlocks.forEach(block => {
                    block.style.display = 'block';
                });
                document.querySelector('.toggle-btn:nth-child(3)').classList.add('active');
            }
            
            // 重新渲染數學公式
            if (window.MathJax) {
                window.MathJax.typeset();
            }
        }
        
        // 頁面加載完成後初始化 MathJax
        document.addEventListener('DOMContentLoaded', function() {
            if (window.MathJax) {
                window.MathJax.typeset();
            }
        });
    </script>
</body>
</html>
"""
    
    # 保存 HTML 文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"HTML 文件已生成: {output_path}")
        return output_path
    except Exception as e:
        print(f"保存 HTML 文件時出錯: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="創建原文/翻譯切換查看 HTML")
    parser.add_argument("json_file", help="翻譯數據 JSON 文件路徑")
    parser.add_argument("--output", "-o", help="輸出 HTML 文件路徑")
    parser.add_argument("--no-copy-images", action="store_true", help="不複製圖片文件")
    args = parser.parse_args()
    
    create_toggle_html(args.json_file, args.output, not args.no_copy_images)

if __name__ == "__main__":
    main()