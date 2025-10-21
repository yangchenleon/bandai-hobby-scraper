#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找HG产品文件夹中没有avatar图像文件的文件夹
"""

import os
import json
from pathlib import Path
from datetime import datetime

def find_missing_avatar_products():
    """查找没有avatar图像文件的HG产品"""
    hg_dir = Path('data/HG')
    
    if not hg_dir.exists():
        print("❌ data/HG 目录不存在")
        return []
    
    missing_avatar_products = []
    
    print("正在扫描HG产品文件夹...")
    
    for product_dir in hg_dir.iterdir():
        if not product_dir.is_dir():
            continue
        
        # 检查是否有JSON文件
        json_file = product_dir / 'product_details.json'
        if not json_file.exists():
            continue
        
        try:
            # 读取JSON文件
            with open(json_file, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            
            product_name = product_data.get('product_name', '')
            avatar = product_data.get('avatar', '')
            
            # 检查主目录下是否有图像文件（除了JSON文件）
            main_images = []
            for file_path in product_dir.iterdir():
                if (file_path.is_file() and 
                    file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp'] and
                    file_path.name != 'product_details.json'):
                    main_images.append(file_path.name)
            
            # 判断是否缺少avatar（只检查根目录是否有图像文件）
            missing_avatar = len(main_images) == 0
            missing_reason = "根目录下没有图像文件" if missing_avatar else ""
            
            if missing_avatar:
                missing_avatar_products.append({
                    'directory': str(product_dir),
                    'product_name': product_name,
                    'avatar_field': avatar,
                    'main_images': main_images,
                    'main_images_count': len(main_images),
                    'missing_reason': missing_reason,
                    'json_file': str(json_file)
                })
                print(f"❌ 缺少avatar: {product_name}")
                print(f"   原因: {missing_reason}")
                print(f"   根目录图像: {len(main_images)} 个")
            else:
                print(f"✅ 有avatar: {product_name}")
                
        except Exception as e:
            print(f"❌ 读取产品 {product_dir.name} 失败: {e}")
            continue
    
    return missing_avatar_products

def save_to_json(missing_products, filename='missing_avatar_products.json'):
    """保存结果到JSON文件"""
    output_data = {
        'total_count': len(missing_products),
        'scan_time': datetime.now().isoformat(),
        'scan_directory': 'data/HG',
        'description': '缺少avatar图像文件的HG产品列表',
        'products': missing_products
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存到: {filename}")
    return filename

def main():
    """主函数"""
    print("=== 查找缺少avatar图像的HG产品 ===")
    
    # 扫描产品
    missing_products = find_missing_avatar_products()
    
    if not missing_products:
        print("\n✅ 所有HG产品都有avatar图像！")
        return
    
    print(f"\n❌ 找到 {len(missing_products)} 个缺少avatar图像的产品")
    
    # 按原因分类统计
    reason_stats = {}
    for product in missing_products:
        reason = product['missing_reason']
        if reason not in reason_stats:
            reason_stats[reason] = 0
        reason_stats[reason] += 1
    
    print(f"\n=== 统计信息 ===")
    for reason, count in reason_stats.items():
        print(f"{reason}: {count} 个产品")
    
    # 保存到JSON
    print(f"\n正在保存结果...")
    json_filename = save_to_json(missing_products)
    
    # 显示详细信息
    print(f"\n=== 详细信息 ===")
    for i, product in enumerate(missing_products, 1):
        print(f"\n{i}. {product['product_name']}")
        print(f"   目录: {product['directory']}")
        print(f"   原因: {product['missing_reason']}")
        print(f"   avatar字段: {product['avatar_field']}")
        print(f"   根目录图像: {product['main_images_count']} 个")
        if product['main_images']:
            print(f"   根目录图像文件: {', '.join(product['main_images'][:3])}{'...' if len(product['main_images']) > 3 else ''}")
    
    print(f"\n=== 扫描完成 ===")
    print(f"总产品数: {len(missing_products)}")
    print(f"结果文件: {json_filename}")

if __name__ == '__main__':
    main()
