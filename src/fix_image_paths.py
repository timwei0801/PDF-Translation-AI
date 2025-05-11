#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復JSON中的圖片路徑，將空路徑與實際存在的圖片匹配起來
"""

import json
import os
import re
import glob
import argparse
from collections import defaultdict

def find_matching_image(base_dir, image_path, filename_pattern, page_num=None, img_num=None):
    """根據模式查找匹配的圖片
    
    Args:
        base_dir: 基礎目錄
        filename_pattern: 文件名模式
        page_num: 頁碼（可選）
        img_num: 圖片編號（可選）
    
    Returns:
        匹配的圖片相對路徑，如果沒有找到則返回None
    """
    # 打印診斷信息
    print(f"尋找圖片: {image_path}")
    print(f"在目錄: {base_dir}")
    
    # 檢查直接路徑
    if not image_path:
        return None
    
    # 先嘗試使用提供的路徑
    full_path = os.path.join(base_dir, image_path)
    if os.path.exists(full_path):
        print(f"找到圖片: {full_path}")
        return image_path
    
    # 遍歷各種可能的路徑模式
    possible_patterns = [
        f"{filename_pattern}*page{page_num}*img{img_num}*",
        f"{filename_pattern}*p{page_num}*i{img_num}*",
        f"*page{page_num}*img{img_num}*",
        f"*p{page_num}*i{img_num}*"
    ]
    
    # 如果只有頁碼
    if page_num and not img_num:
        possible_patterns.extend([
            f"{filename_pattern}*page{page_num}*",
            f"{filename_pattern}*p{page_num}*",
            f"*page{page_num}*"
        ])
    
    # 使用通配符查找
    for pattern in possible_patterns:
        for img_format in ['png', 'jpg', 'jpeg', 'gif']:
            matches = glob.glob(os.path.join(base_dir, "**", f"{pattern}.{img_format}"), recursive=True)
            if matches:
                return os.path.relpath(matches[0], base_dir)
    
    return None

def fix_image_paths(json_path, save=True):
    """修復JSON中的圖片路徑
    
    根據圖片文件名中的頁碼和圖片編號，將圖片與JSON中的區塊匹配起來
    
    Args:
        json_path: JSON文件路徑
        save: 是否保存修復後的JSON
    
    Returns:
        修復後的JSON數據
    """
    # 讀取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 獲取JSON文件所在目錄
    base_dir = os.path.dirname(json_path)
    
    # 獲取所有可用的圖片
    available_images = []
    for pattern in ['*.png', '*.jpg', '*.jpeg', '*.gif']:
        available_images.extend(glob.glob(os.path.join(base_dir, '**', pattern), recursive=True))
    
    # 圖片字典，按頁碼和圖片編號索引
    image_dict = defaultdict(dict)
    base_name = os.path.splitext(os.path.basename(json_path))[0].split('_translation_data')[0]
    
    # 解析圖片名稱中的頁碼和圖片編號
    for img_path in available_images:
        img_name = os.path.basename(img_path)
        
        # 嘗試不同的模式匹配
        patterns = [
            r'page(\d+)_img(\d+)',   # 標準模式: page1_img2
            r'p(\d+)_i(\d+)',        # 簡化模式: p1_i2
            r'page(\d+)',            # 只有頁碼: page1
            r'p(\d+)'                # 簡化頁碼: p1
        ]
        
        for pattern in patterns:
            match = re.search(pattern, img_name)
            if match:
                if len(match.groups()) == 2:  # 有頁碼和圖片編號
                    page_num = int(match.group(1))
                    img_num = int(match.group(2))
                    image_dict[page_num][img_num] = os.path.relpath(img_path, base_dir)
                    print(f"找到圖片: 頁面 {page_num}, 圖片 {img_num}: {img_path}")
                elif len(match.groups()) == 1:  # 只有頁碼
                    page_num = int(match.group(1))
                    # 使用默認編號0，表示這是整頁的圖片
                    image_dict[page_num][0] = os.path.relpath(img_path, base_dir)
                    print(f"找到頁面圖片: 頁面 {page_num}: {img_path}")
                break
    
    # 更新JSON中的圖片路徑
    fixed_count = 0
    for page_idx, page in enumerate(data.get("text_data", [])):
        page_num = page_idx + 1
        img_count = 0
        
        for block_idx, block in enumerate(page.get("blocks", [])):
            if block.get("type") in ["image", "figure"] and not block.get("image_path"):
                img_count += 1
                
                # 嘗試從圖片字典中查找
                if page_num in image_dict and img_count in image_dict[page_num]:
                    # 從字典中找到匹配的圖片
                    block["image_path"] = image_dict[page_num][img_count]
                    fixed_count += 1
                    print(f"修復圖片路徑: 頁面 {page_num}, 區塊 {block_idx}, 路徑 {block['image_path']}")
                else:
                    # 嘗試使用模式匹配查找
                    matched_path = find_matching_image(base_dir, base_name, page_num, img_count)
                    if matched_path:
                        block["image_path"] = matched_path
                        fixed_count += 1
                        print(f"使用模式匹配修復圖片路徑: 頁面 {page_num}, 區塊 {block_idx}, 路徑 {matched_path}")
    
    print(f"\n總共修復了 {fixed_count} 個圖片路徑")
    
    # 保存修復後的JSON
    if save:
        output_path = json_path.replace('.json', '_fixed.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存修復後的JSON到: {output_path}")
    
    return data

def main():
    parser = argparse.ArgumentParser(description="修復JSON中的圖片路徑")
    parser.add_argument("json_file", help="JSON文件路徑")
    parser.add_argument("--no-save", action="store_true", help="不保存修復後的JSON")
    args = parser.parse_args()
    
    fix_image_paths(args.json_file, not args.no_save)

if __name__ == "__main__":
    main()