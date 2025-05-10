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
    image_dict = {}
    base_name = os.path.splitext(os.path.basename(json_path))[0].split('_translation_data')[0]
    
    # 解析圖片名稱中的頁碼和圖片編號
    for img_path in available_images:
        img_name = os.path.basename(img_path)
        
        # 嘗試匹配 "page{頁碼}_img{圖片編號}" 模式
        match = re.search(r'page(\d+)_img(\d+)', img_name)
        if match:
            page_num = int(match.group(1))
            img_num = int(match.group(2))
            
            if page_num not in image_dict:
                image_dict[page_num] = {}
            
            image_dict[page_num][img_num] = os.path.relpath(img_path, base_dir)
            print(f"找到圖片: 頁面 {page_num}, 圖片 {img_num}: {img_path}")
    
    # 更新JSON中的圖片路徑
    fixed_count = 0
    for page_idx, page in enumerate(data.get("text_data", [])):
        page_num = page_idx + 1
        img_count = 0
        
        for block_idx, block in enumerate(page.get("blocks", [])):
            if block.get("type") in ["image", "figure"] and not block.get("image_path"):
                if page_num in image_dict:
                    # 嘗試匹配圖片
                    img_count += 1
                    if img_count in image_dict[page_num]:
                        # 找到匹配的圖片
                        block["image_path"] = image_dict[page_num][img_count]
                        fixed_count += 1
                        print(f"修復圖片路徑: 頁面 {page_num}, 區塊 {block_idx}, 路徑 {block['image_path']}")
    
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