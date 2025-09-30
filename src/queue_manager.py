#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
队列管理模块
管理待处理队列和失败队列
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from models import ProductLink


class QueueManager:
    """队列管理器"""
    
    def __init__(self, db_path: str = "bandai_hobby.db"):
        self.db_path = db_path
        self.init_queues()
    
    def init_queues(self):
        """初始化队列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 待处理队列表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                product_name TEXT,
                page_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # 失败队列表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failed_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                product_name TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_retry_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_to_pending_queue(self, product_links: List[ProductLink], page_number: int = 0):
        """添加产品链接到待处理队列"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        added_count = 0
        skipped_existing_count = 0
        for link in product_links:
            try:
                # 如果产品已在products表中存在，则跳过加入pending
                cursor.execute('''
                    INSERT INTO pending_queue (url, product_name, page_number)
                    SELECT ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM products WHERE url = ?
                    )
                    ON CONFLICT(url) DO NOTHING
                ''', (link.href, link.text, page_number, link.href))
                if cursor.rowcount > 0:
                    added_count += 1
                else:
                    # 判断是因为已存在于products而跳过，还是因为pending_queue已存在
                    cursor.execute('SELECT 1 FROM products WHERE url = ? LIMIT 1', (link.href,))
                    if cursor.fetchone():
                        skipped_existing_count += 1
            except Exception as e:
                print(f"添加链接到待处理队列失败: {link.href} - {e}")
        
        conn.commit()
        conn.close()
        print(f"✅ 已添加 {added_count} 个产品到待处理队列，跳过已存在产品 {skipped_existing_count} 个")
        return added_count
    
    def get_pending_products(self, limit: int = 10) -> List[Dict]:
        """获取待处理的产品"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, url, product_name, page_number, created_at
            FROM pending_queue 
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT ?
        ''', (limit,))
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row[0],
                'url': row[1],
                'product_name': row[2],
                'page_number': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        return products
    
    def mark_as_processing(self, queue_id: int):
        """标记为处理中"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pending_queue 
            SET status = 'processing'
            WHERE id = ?
        ''', (queue_id,))
        
        conn.commit()
        conn.close()
    
    def mark_as_completed(self, queue_id: int):
        """标记为已完成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pending_queue 
            SET status = 'completed'
            WHERE id = ?
        ''', (queue_id,))
        
        conn.commit()
        conn.close()
    
    def add_to_failed_queue(self, url: str, product_name: str, error_message: str):
        """添加失败的产品到失败队列"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO failed_queue (url, product_name, error_message, retry_count)
            VALUES (?, ?, ?, 1)
        ''', (url, product_name, error_message))
        
        conn.commit()
        conn.close()
        print(f"❌ 已添加失败产品到失败队列: {product_name}")
    
    def get_queue_stats(self) -> Dict:
        """获取队列统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 待处理队列统计
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM pending_queue 
            GROUP BY status
        ''')
        pending_stats = dict(cursor.fetchall())
        
        # 失败队列统计
        cursor.execute('SELECT COUNT(*) FROM failed_queue')
        failed_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'pending': pending_stats.get('pending', 0),
            'processing': pending_stats.get('processing', 0),
            'completed': pending_stats.get('completed', 0),
            'failed': failed_count
        }
    
    def reset_processing_to_pending(self):
        """重置所有处理中的任务为待处理状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找处理中的任务数量
        cursor.execute('SELECT COUNT(*) FROM pending_queue WHERE status = "processing"')
        processing_count = cursor.fetchone()[0]
        
        if processing_count > 0:
            print(f"发现 {processing_count} 个处理中的任务，重置为待处理状态")
            cursor.execute('''
                UPDATE pending_queue 
                SET status = 'pending'
                WHERE status = 'processing'
            ''')
            conn.commit()
            print(f"✅ 已重置 {processing_count} 个任务为待处理状态")
        else:
            print("没有发现处理中的任务")
        
        conn.close()
        return processing_count

    def clear_completed(self):
        """清理已完成的项目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM pending_queue WHERE status = "completed"')
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        print(f"✅ 已清理 {deleted_count} 个已完成的项目")
        return deleted_count
