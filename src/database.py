import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from minio import Minio
from minio.error import S3Error
import hashlib

class DatabaseManager:
    def __init__(self, db_path: str = "database/bandai_hobby.db"):
        self.db_path = db_path
        # 确保数据库目录存在
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            print(f"创建数据库目录失败: {e}")
        self.init_database()
        
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 产品表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                price TEXT,
                release_date TEXT,
                article_content TEXT,
                url TEXT UNIQUE NOT NULL,
                product_tag TEXT,
                series TEXT,
                brand TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 图像表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                image_filename TEXT NOT NULL,
                image_hash TEXT UNIQUE,
                minio_path TEXT,
                type TEXT DEFAULT 'detail',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_product(self, product_data: Dict) -> int:
        """添加产品到数据库，使用UPSERT确保相同URL返回相同ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 先尝试插入，如果URL已存在则更新
        cursor.execute('''
            INSERT INTO products 
            (product_name, price, release_date, article_content, url, product_tag, series, brand)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                product_name = excluded.product_name,
                price = excluded.price,
                release_date = excluded.release_date,
                article_content = excluded.article_content,
                product_tag = excluded.product_tag,
                series = excluded.series,
                brand = excluded.brand
        ''', (
            product_data['product_name'],
            product_data['product_info'].get('価格'),
            product_data['product_info'].get('発売日'),
            product_data['article_content'],
            product_data['url'],
            product_data.get('product_tag', ''),
            product_data.get('series', ''),
            product_data.get('brand', '')
        ))
        
        # 获取产品ID（无论是否新插入或更新）
        cursor.execute("SELECT id FROM products WHERE url = ?", (product_data['url'],))
        result = cursor.fetchone()
        product_id = result[0] if result else None
        
        conn.commit()
        conn.close()
        return product_id
    
    def add_image(self, product_id: int, image_filename: str, image_path: str, image_type: str = 'detail') -> int:
        """添加图像记录到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 计算图像哈希
        with open(image_path, 'rb') as f:
            image_hash = hashlib.md5(f.read()).hexdigest()
        
        cursor.execute('''
            INSERT OR IGNORE INTO images (product_id, image_filename, image_hash, minio_path, type)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, image_filename, image_hash, None, image_type))
        
        image_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return image_id
    
    def update_image_minio_path(self, image_id: int, minio_path: str):
        """更新图像的MinIO路径"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE images SET minio_path = ? WHERE id = ?
        ''', (minio_path, image_id))
        
        conn.commit()
        conn.close()
    
    def get_products(self) -> List[Dict]:
        """获取所有产品"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, product_name, price, release_date, 
                   article_content, url, images_downloaded, download_timestamp, created_at
            FROM products ORDER BY created_at DESC
        ''')
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row[0],
                'product_name': row[1],
                'price': row[2],
                'release_date': row[3], 
                'article_content': row[4],
                'url': row[5],
                'images_downloaded': bool(row[6]),
                'download_timestamp': row[7],
                'created_at': row[8]
            })
        
        conn.close()
        return products
    
    def get_product_images(self, product_id: int) -> List[Dict]:
        """获取产品的图像列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, image_filename, image_hash, minio_path, type, created_at
            FROM images WHERE product_id = ? ORDER BY created_at
        ''', (product_id,))
        
        images = []
        for row in cursor.fetchall():
            images.append({
                'id': row[0],
                'image_filename': row[1],
                'image_hash': row[2],
                'minio_path': row[3],
                'type': row[4],
                'created_at': row[5]
            })
        
        conn.close()
        return images
    
    def get_products_without_details(self) -> List[Dict]:
        """获取未爬取详情的产品（article_content为空或NULL）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, url, created_at
            FROM products 
            WHERE series IS NULL OR series = ''
            ORDER BY created_at
        ''')
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row[0],
                'url': row[1],
                'created_at': row[2]
            })
        
        conn.close()
        return products


class MinIOClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket_name: str = "bandai-hobby"):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        self.bucket_name = bucket_name
        self.ensure_bucket()
    
    def ensure_bucket(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"MinIO错误: {e}")
    
    def upload_image(self, image_path: str, object_name: str) -> str:
        """上传图像到MinIO"""
        try:
            self.client.fput_object(self.bucket_name, object_name, image_path)
            return f"{self.bucket_name}/{object_name}"
        except S3Error as e:
            print(f"上传图像失败: {e}")
            return None
    
    def get_image_url(self, object_name: str) -> str:
        """获取图像的访问URL"""
        try:
            return self.client.presigned_get_object(self.bucket_name, object_name)
        except S3Error as e:
            print(f"获取图像URL失败: {e}")
            return None
