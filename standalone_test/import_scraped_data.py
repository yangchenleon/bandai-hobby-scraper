#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 scraped_data.json 导入产品表的一次性脚本
使用 UPSERT 确保相同URL总是返回相同ID，避免MinIO文件夹重复创建
"""

import json
import sqlite3
from pathlib import Path


def import_scraped_data():
    """导入 scraped_data.json 到产品表"""
    
    # 检查文件是否存在
    json_file = Path("data/scraped_data.json")
    if not json_file.exists():
        print(f"❌ 文件不存在: {json_file}")
        return
    
    # 检查数据库是否存在
    db_file = Path("/mnt/d/code/bandai-hobby-scraper/database/bandai_hobby.db")
    if not db_file.exists():
        print(f"❌ 数据库不存在: {db_file}")
        return
    
    try:
        # 读取 JSON 数据
        with open(json_file, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
        
        print(f"📖 读取到 {len(scraped_data)} 条数据")
        
        # 连接数据库
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 检查当前产品表中的记录数
        cursor.execute("SELECT COUNT(*) FROM products")
        existing_count = cursor.fetchone()[0]
        print(f"📊 数据库中现有 {existing_count} 条产品记录")
        
        # 导入数据
        imported_count = 0
        skipped_count = 0
        
        for item in scraped_data:
            href = item.get('href', '')
            
            if not href:
                print(f"⚠️ 跳过无效数据: {item}")
                skipped_count += 1
                continue
            
            try:
                # 使用 UPSERT 避免ID跳跃，确保相同URL总是返回相同ID
                cursor.execute('''
                    INSERT INTO products (url) 
                    VALUES (?) 
                    ON CONFLICT(url) DO NOTHING
                ''', (href,))
                
                # 获取产品ID（无论是否新插入）
                cursor.execute("SELECT id FROM products WHERE url = ?", (href,))
                result = cursor.fetchone()
                product_id = result[0] if result else None
                
                if cursor.rowcount > 0:
                    imported_count += 1
                    if imported_count <= 5:  # 只显示前5条
                        print(f"✅ 新导入: {href} (ID: {product_id})")
                else:
                    skipped_count += 1
                    if skipped_count <= 5:  # 显示前5条跳过的记录
                        print(f"🔄 已存在: {href} (ID: {product_id})")
                    
            except Exception as e:
                print(f"❌ 导入失败: {href} -> {e}")
                skipped_count += 1
        
        # 提交事务
        conn.commit()
        conn.close()
        
        print(f"\n📊 导入完成:")
        print(f"  - 新导入: {imported_count} 条")
        print(f"  - 已存在: {skipped_count} 条")
        print(f"  - 总计处理: {len(scraped_data)} 条")
        print(f"  - 数据库记录总数: {imported_count + skipped_count} 条")
        
        # 验证导入结果
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        final_count = cursor.fetchone()[0]
        print(f"  - 数据库最终记录数: {final_count} 条")
        conn.close()
        
    except Exception as e:
        print(f"❌ 导入过程中出错: {e}")

def show_sample_data():
    """显示导入后的样本数据"""
    db_file = Path("/mnt/d/code/bandai-hobby-scraper/database/bandai_hobby.db")
    if not db_file.exists():
        print(f"❌ 数据库不存在: {db_file}")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 显示前10条记录
        cursor.execute('''
            SELECT id, url, created_at 
            FROM products 
            ORDER BY id 
            LIMIT 10
        ''')
        
        records = cursor.fetchall()
        
        print(f"\n📋 前10条产品记录:")
        print("-" * 80)
        for record in records:
            print(f"ID: {record[0]}")
            print(f"URL: {record[1]}")
            print(f"创建时间: {record[2]}")
            print("-" * 40)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 查看数据时出错: {e}")

if __name__ == "__main__":
    print("🚀 开始导入 scraped_data.json 到产品表")
    print("=" * 50)
    
    import_scraped_data()
    
    print("\n" + "=" * 50)
    show_sample_data()
