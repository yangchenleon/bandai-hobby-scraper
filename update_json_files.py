#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新现有JSON文件，移除images_downloaded字段
"""

import os
import json
import glob
from pathlib import Path

def update_json_files():
    """更新所有产品JSON文件，移除images_downloaded字段"""
    data_dir = Path("data")
    
    # 查找所有产品文件夹
    product_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name != "scraped_data.json"]
    
    print(f"找到 {len(product_dirs)} 个产品文件夹")
    
    updated_count = 0
    for product_dir in product_dirs:
        json_file = product_dir / "product_details.json"
        
        if json_file.exists():
            try:
                # 读取JSON文件
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否有需要更新或移除的字段
                updated = False
                changes = []
                
                # 移除不需要的字段
                fields_to_remove = ['images_downloaded', 'download_timestamp']
                for field in fields_to_remove:
                    if field in data:
                        del data[field]
                        changes.append(f"移除{field}")
                        updated = True
                
                # 重命名字段
                if 'series_links' in data:
                    data['series'] = data['series_links']
                    del data['series_links']
                    changes.append("series_links -> series")
                    updated = True
                
                if updated:
                    # 保存更新后的文件
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ 已更新: {product_dir.name} ({'; '.join(changes)})")
                    updated_count += 1
                else:
                    print(f"ℹ️ 无需更新: {product_dir.name}")
                    
            except Exception as e:
                print(f"❌ 更新失败: {product_dir.name} - {e}")
    
    print(f"\n更新完成！共更新了 {updated_count} 个文件")

if __name__ == "__main__":
    update_json_files()
