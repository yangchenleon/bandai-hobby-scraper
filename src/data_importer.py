import os
import json
import glob
import sqlite3
from pathlib import Path
from typing import List, Dict
from database import DatabaseManager, MinIOClient
from config import Config

class DataImporter:
    def __init__(self):
        self.db = DatabaseManager(Config.DATABASE_PATH)
        self.minio = MinIOClient(**Config.get_minio_config())
    
    def import_all_data(self):
        """导入data文件夹中的所有数据"""
        data_dir = Path(Config.DATA_DIR)
        
        # 查找所有产品文件夹
        product_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name != "scraped_data.json"]
        
        print(f"找到 {len(product_dirs)} 个产品文件夹")
        
        for product_dir in product_dirs:
            try:
                self.import_product(product_dir)
                print(f"✓ 导入完成: {product_dir.name}")
            except Exception as e:
                print(f"✗ 导入失败: {product_dir.name} - {e}")
    
    def import_product(self, product_dir: Path):
        """导入单个产品数据"""
        # 读取产品详情JSON
        json_file = product_dir / "product_details.json"
        if not json_file.exists():
            raise FileNotFoundError(f"未找到产品详情文件: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            product_data = json.load(f)
        
        # 添加产品到数据库
        product_id = self.db.add_product(product_data)
        
        # 处理图像
        images_dir = product_dir / "images"
        if images_dir.exists():
            self.import_product_images(product_id, images_dir, product_data['product_name'])
        else:
            print(f"  ⚠️ 未找到图片目录: {images_dir}")
    
    def import_product_images(self, product_id: int, images_dir: Path, product_name: str):
        """导入产品图像"""
        # 检查MinIO中是否已存在该产品的图片
        if self._check_minio_images_exist(product_id):
            return
        
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg")) + list(images_dir.glob("*.png"))
        
        if not image_files:
            return

        
        for image_file in image_files:
            try:
                # 生成MinIO对象名称
                object_name = f"products/{product_id}/{image_file.name}"
                
                # 上传到MinIO
                minio_path = self.minio.upload_image(str(image_file), object_name)
                
                if minio_path:
                    # 添加到数据库
                    image_id = self.db.add_image(product_id, image_file.name, str(image_file))
                    self.db.update_image_minio_path(image_id, minio_path)
                else:
                    print(f"    ✗ 图像上传失败: {image_file.name}")
                    
            except Exception as e:
                print(f"    ✗ 处理图像失败: {image_file.name} - {e}")
    
    def _check_minio_images_exist(self, product_id: int) -> bool:
        """检查MinIO中是否已存在该产品的图片"""
        try:
            # 检查MinIO中是否存在该产品的文件夹
            prefix = f"products/{product_id}/"
            objects = list(self.minio.client.list_objects(
                self.minio.bucket_name, 
                prefix=prefix, 
                recursive=True
            ))
            
            # 过滤出图片文件
            image_objects = [obj for obj in objects if obj.object_name.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            if image_objects:
                return True
            
            return False
            
        except Exception as e:
            print(f"    ⚠️ 检查MinIO图片时出错: {e}")
            # 如果检查失败，为了安全起见，不跳过处理
            return False
    
    def sync_database_with_minio(self):
        """同步数据库记录与MinIO实际文件，清理不一致的数据"""
        print("🔄 开始同步数据库与MinIO...")
        
        products = self.db.get_products()
        cleaned_count = 0
        
        for product in products:
            product_id = product['id']
            
            # 检查MinIO中是否存在该产品的图片
            if not self._check_minio_images_exist(product_id):
                # MinIO中没有图片，但数据库中有记录，清理数据库记录
                print(f"  🧹 清理产品ID {product_id} 的无效图片记录")
                self._clean_product_images_from_db(product_id)
                cleaned_count += 1
        
        print(f"✅ 同步完成，清理了 {cleaned_count} 个产品的无效记录")
    
    def _clean_product_images_from_db(self, product_id: int):
        """从数据库中清理指定产品的图片记录"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # 删除图片记录
            cursor.execute("DELETE FROM images WHERE product_id = ?", (product_id,))
            
            # 更新产品的图片下载状态
            cursor.execute("""
                UPDATE products 
                SET images_downloaded = FALSE, download_timestamp = NULL 
                WHERE id = ?
            """, (product_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"    ❌ 清理产品ID {product_id} 的记录时出错: {e}")
    
    def get_import_stats(self) -> Dict:
        """获取导入统计信息"""
        products = self.db.get_products()
        total_images = 0
        
        for product in products:
            images = self.db.get_product_images(product['id'])
            total_images += len(images)
        
        return {
            "total_products": len(products),
            "total_images": total_images,
            "products_with_images": len([p for p in products if p['images_downloaded']])
        }

def main():
    """主函数"""
    import sys
    
    importer = DataImporter()
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--sync":
        # 同步模式：清理数据库与MinIO不一致的记录
        importer.sync_database_with_minio()
    else:
        # 正常导入模式
        print("开始导入数据...")
        importer.import_all_data()
    
    print("\n统计信息:")
    stats = importer.get_import_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
