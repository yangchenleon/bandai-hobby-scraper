#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
队列查看工具
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from queue_manager import QueueManager
from config import Config

def view_queue_stats():
    """查看队列统计信息"""
    queue_manager = QueueManager(Config.DATABASE_PATH)
    stats = queue_manager.get_queue_stats()
    
    print("=== 队列统计信息 ===")
    print(f"待处理: {stats['pending']}")
    print(f"处理中: {stats['processing']}")
    print(f"已完成: {stats['completed']}")
    print(f"失败: {stats['failed']}")
    print(f"总计: {sum(stats.values())}")

def view_pending_queue(limit=20):
    """查看待处理队列"""
    queue_manager = QueueManager(Config.DATABASE_PATH)
    products = queue_manager.get_pending_products(limit)
    
    print(f"\n=== 待处理队列 (显示前 {limit} 个) ===")
    if not products:
        print("队列为空")
        return
    
    for i, product in enumerate(products, 1):
        print(f"{i}. {product['product_name']}")
        print(f"   URL: {product['url']}")
        print(f"   页码: {product['page_number']}")
        print(f"   创建时间: {product['created_at']}")
        print()

def view_failed_queue(limit=20):
    """查看失败队列"""
    import sqlite3
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT url, product_name, error_message, retry_count, created_at
        FROM failed_queue 
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    
    products = cursor.fetchall()
    conn.close()
    
    print(f"\n=== 失败队列 (显示前 {limit} 个) ===")
    if not products:
        print("失败队列为空")
        return
    
    for i, product in enumerate(products, 1):
        print(f"{i}. {product[1]}")
        print(f"   URL: {product[0]}")
        print(f"   错误: {product[2]}")
        print(f"   重试次数: {product[3]}")
        print(f"   创建时间: {product[4]}")
        print()

def clear_failed_queue():
    """清空失败队列"""
    import sqlite3
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM failed_queue')
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute('DELETE FROM failed_queue')
        conn.commit()
        print(f"✅ 已清空失败队列，删除了 {count} 个记录")
    else:
        print("失败队列为空")
    
    conn.close()

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "stats":
            view_queue_stats()
        elif command == "pending":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            view_pending_queue(limit)
        elif command == "failed":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            view_failed_queue(limit)
        elif command == "clear-failed":
            clear_failed_queue()
        else:
            print("未知命令")
    else:
        print("用法:")
        print("  python view_queue.py stats              # 查看统计信息")
        print("  python view_queue.py pending [数量]     # 查看待处理队列")
        print("  python view_queue.py failed [数量]      # 查看失败队列")
        print("  python view_queue.py clear-failed       # 清空失败队列")

if __name__ == "__main__":
    main()
