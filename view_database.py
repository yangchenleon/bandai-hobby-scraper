#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看 SQLite 数据库内容的脚本
"""

import sqlite3
import json
from pathlib import Path

def view_database(db_path="database/bandai_hobby.db"):
    """查看数据库内容"""
    
    if not Path(db_path).exists():
        print(f"❌ 数据库文件 {db_path} 不存在")
        return
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📊 数据库: {db_path}")
        print("=" * 50)
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ 数据库中没有表")
            return
        
        print(f"📋 找到 {len(tables)} 个表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        print("\n" + "=" * 50)
        
        # 查看每个表的内容
        for table_name in tables:
            table_name = table_name[0]
            print(f"\n📋 表: {table_name}")
            print("-" * 30)
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            print("列信息:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"\n记录数: {count}")
            
            if count > 0:
                # 显示前几条记录
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                
                print("\n前5条记录:")
                for i, row in enumerate(rows, 1):
                    print(f"  {i}. {row}")
                
                if count > 5:
                    print(f"  ... 还有 {count - 5} 条记录")
        
        conn.close()
        print("\n✅ 数据库查看完成")
        
    except Exception as e:
        print(f"❌ 查看数据库时出错: {e}")

def view_products_only(db_path="bandai_hobby.db"):
    """只查看产品表的内容"""
    
    if not Path(db_path).exists():
        print(f"❌ 数据库文件 {db_path} 不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📊 产品数据: {db_path}")
        print("=" * 50)
        
        # 查看产品表
        cursor.execute("SELECT COUNT(*) FROM products;")
        count = cursor.fetchone()[0]
        print(f"产品总数: {count}")
        
        if count > 0:
            # 显示产品列表
            cursor.execute("""
                SELECT id, name, url, created_at 
                FROM products 
                ORDER BY created_at DESC 
                LIMIT 10;
            """)
            products = cursor.fetchall()
            
            print(f"\n📋 最近10个产品:")
            print("-" * 50)
            for product in products:
                print(f"ID: {product[0]}")
                print(f"名称: {product[1]}")
                print(f"URL: {product[2]}")
                print(f"创建时间: {product[3]}")
                print("-" * 30)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 查看产品数据时出错: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "products":
        view_products_only()
    else:
        view_database()
