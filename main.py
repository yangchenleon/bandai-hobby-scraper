#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万代模型爬虫主程序
"""

import sys
import os
import re
from urllib.parse import urljoin

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scraper import BandaiScraper


def load_products_from_json(json_file_path: str = 'data/scraped_data.json'):
    """
    从JSON文件加载产品列表
    
    Args:
        json_file_path: JSON文件路径
        
    Returns:
        list: ProductLink对象列表，失败时返回空列表
    """
    try:
        import json
        from models import ProductLink
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        print(f"从JSON文件读取到 {len(saved_data)} 个产品")
        
        # 转换为ProductLink对象
        product_links = []
        for item in saved_data:
            product_link = ProductLink(
                href=item['href'],
                text=item['text']
            )
            product_links.append(product_link)
        
        print(f"成功加载 {len(product_links)} 个产品链接")
        return product_links
        
    except FileNotFoundError:
        print(f"❌ JSON文件不存在: {json_file_path}")
        return []
    except Exception as e:
        print(f"❌ 读取JSON文件失败: {e}")
        return []


def scrape_product_details_batch(scraper, product_links, max_products=10):
    """
    批量爬取产品详情
    
    Args:
        scraper: 爬虫实例
        product_links: 产品链接列表
        max_products: 最大处理产品数量
        
    Returns:
        tuple: (成功数量, 失败数量)
    """
    print("\n" + "=" * 50)
    print("=== 开始爬取产品详情 ===")
    
    success_count = 0
    failed_count = 0
    
    # 处理所有产品，或者限制数量进行测试
    products_to_process = product_links[:max_products]
    
    for i, product_link in enumerate(products_to_process, 1):
        print(f"\n--- 处理产品 {i}/{len(products_to_process)} ---")
        print(f"产品名称: {product_link.text}")
        print(f"产品链接: {product_link.href}")
        
        # 检查链接是否有效
        if not product_link.href:
            print("❌ 产品链接为空，跳过")
            failed_count += 1
            continue
        
        # 构建完整URL
        if product_link.href.startswith('http'):
            product_url = product_link.href
        else:
            from config import PRODUCT_LIST_URL
            product_url = urljoin(PRODUCT_LIST_URL, product_link.href)
        
        # 创建产品文件夹        
        base_dir = 'data'
        
        try:
            # 爬取产品详情
            product_details = scraper.scrape_product_details(product_url, base_dir)
            # print(product_details)
            if product_details:
                print(f"✅ 产品详情爬取成功！")
                success_count += 1
            else:
                print(f"❌ 产品详情爬取失败")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ 处理产品时发生错误: {str(e)}")
            failed_count += 1
    
        return success_count, failed_count


def scrape_products_from_database(scraper, products, max_products, db):
    """
    从数据库获取的产品列表中批量爬取产品详情
    
    Args:
        scraper: 爬虫实例
        products: 产品列表（从数据库获取）
        max_products: 最大处理产品数量
        db: 数据库管理器
        
    Returns:
        tuple: (成功数量, 失败数量)
    """
    print("\n" + "=" * 50)
    print("=== 开始爬取产品详情 ===")
    
    success_count = 0
    failed_count = 0
    
    # 处理指定数量的产品
    products_to_process = products[:max_products]
    
    for i, product in enumerate(products_to_process, 1):
        print(f"\n--- 处理产品 {i}/{len(products_to_process)} ---")
        print(f"产品ID: {product['id']}")
        print(f"产品链接: {product['url']}")
        
        # 检查链接是否有效
        if not product['url']:
            print("❌ 产品链接为空，跳过")
            failed_count += 1
            continue
        
        # 创建产品文件夹        
        # base_dir = 'data'
        # product_name = product['product_name'] or f"product_{product['id']}"
        
        # # 清理文件夹名称
        # safe_folder_name = re.sub(r'[<>:"/\\|?*]', '_', product_name)
        # safe_folder_name = re.sub(r'\s+', ' ', safe_folder_name).strip()
        # safe_folder_name = safe_folder_name.strip('.')
        # if len(safe_folder_name) > 100:
        #     safe_folder_name = safe_folder_name[:100]
        
        # product_dir = os.path.join(base_dir, safe_folder_name)
        product_dir = 'data'
        
        try:
            # 爬取产品详情
            print(f"正在爬取产品详情...")
            product_details = scraper.scrape_product_details(
                product_url=product['url'], 
                output_path=product_dir
            )
            
            if product_details:
                print(f"✅ 产品详情爬取成功")
                success_count += 1
            else:
                print(f"❌ 产品详情爬取失败")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ 处理产品时出错: {e}")
            failed_count += 1
    
    return success_count, failed_count


def main():
    """
    主函数
    """
    print("万代模型爬虫启动...")
    print("=" * 50)
    
    # 创建爬虫实例
    scraper = BandaiScraper()
    page, detail, import_data = 0,1,1
    MAX_PRODUCTS = 6  # 最大处理产品数量，可以根据需要调整
    
    if page:
        # 1. 爬取产品列表（多页）
        num_pages = scraper.get_total_pages()
        num_pages = 5
        print(f"=== 爬取产品列表（最多 {num_pages} 页） ===")
        list_result = scraper.scrape_product_list(num_pages=num_pages, start_page=1)
        print(f"\n产品列表爬取完成！共找到 {len(list_result.data)} 个产品")
    
    if detail:
        # 2. 从数据库获取未爬取详情的产品URL
        print("\n=== 从数据库获取未爬取详情的产品 ===")
        from database import DatabaseManager
        from config import Config
        
        db = DatabaseManager(Config.DATABASE_PATH)
        products_to_scrape = db.get_products_without_details()
        
        if products_to_scrape:
            print(f"找到 {len(products_to_scrape)} 个未爬取详情的产品")
            
            # 批量爬取产品详情
            success_count, failed_count = scrape_products_from_database(
                scraper, products_to_scrape, MAX_PRODUCTS, db
            )
            
            # 输出总结
            print("\n" + "=" * 50)
            print("=== 爬取完成 ===")
            print(f"成功处理: {success_count} 个产品")
            print(f"失败: {failed_count} 个产品")
            print(f"本次处理: {min(MAX_PRODUCTS, len(products_to_scrape))} 个产品")
            print(f"数据库中未处理: {len(products_to_scrape)} 个产品")
        else:
            print("✅ 所有产品详情已爬取完成！")

    if import_data:# 3. 导入爬取的数据到数据库
        print("\n=== 开始导入数据到数据库 ===")
        try:    
            from data_importer import DataImporter
            
            importer = DataImporter()
            importer.import_all_data()
            print(f"✅ 数据导入完成")
        except Exception as e:
            print(f"❌ 数据导入失败: {e}")


if __name__ == "__main__":
    main()
