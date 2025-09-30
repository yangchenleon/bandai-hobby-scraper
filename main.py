#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万代模型爬虫主程序
"""

import sys
import os
import re
from pathlib import Path
from urllib.parse import urljoin

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import PRODUCT_LIST_URL
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
            result = scraper.scrape_product_details(product_url, base_dir)
            if result:
                product_details, product_dir = result
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
            result = scraper.scrape_product_details(
                product_url=product['url'], 
                output_path=product_dir
            )
            
            if result:
                product_details, product_dir = result
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
    
    # 创建爬虫实例和队列管理器
    scraper = BandaiScraper()
    from queue_manager import QueueManager
    from database import DatabaseManager
    from config import Config
    from data_importer import DataImporter
    
    queue_manager = QueueManager(Config.DATABASE_PATH)
    db = DatabaseManager(Config.DATABASE_PATH)
    importer = DataImporter()
    
    # 重置处理中的任务为待处理状态
    print("=== 检查并重置处理中的任务 ===")
    queue_manager.reset_processing_to_pending()
    
    # 配置参数
    start_page = 1
    end_page = 2
    batch_size = 10
    brand = "mg"
    base_url = PRODUCT_LIST_URL + brand + '/'
    
    # 1. 爬取产品列表并添加到待处理队列
    print(f"=== 爬取产品列表（第 {start_page} 到 {end_page} 页） ===")
    for page_num in range(start_page, end_page + 1):
        print(f"\n正在爬取第 {page_num} 页...")
        list_result = scraper.scrape_product_list(num_pages=1, start_page=page_num, base_url=base_url)
        
        if list_result.success and list_result.data:
            added_count = queue_manager.add_to_pending_queue(list_result.data, page_num)
            print(f"第 {page_num} 页添加了 {added_count} 个产品到待处理队列")
        else:
            print(f"第 {page_num} 页爬取失败")
    
    # 显示队列统计
    stats = queue_manager.get_queue_stats()
    print(f"\n队列统计: 待处理 {stats['pending']}, 处理中 {stats['processing']}, 已完成 {stats['completed']}, 失败 {stats['failed']}")

    # 2. 从待处理队列获取产品进行详情爬取
    print("\n=== 开始处理待处理队列 ===")
    
    success_count = 0
    failed_count = 0
    
    while True:
        # 获取待处理的产品
        pending_products = queue_manager.get_pending_products(batch_size)
        
        if not pending_products:
            print("✅ 待处理队列为空，处理完成！")
            break
        
        print(f"\n获取到 {len(pending_products)} 个待处理产品")
        
        for product in pending_products:
            print(f"\n--- 处理产品: {product['product_name']} ---")
            print(f"URL: {product['url']}")
            
            # 标记为处理中
            queue_manager.mark_as_processing(product['id'])
            
            try:
                # 爬取产品详情
                result = scraper.scrape_product_details(
                    product_url=product['url'], 
                    output_path='data',
                    queue_product_name=product['product_name']
                )
                
                if result:
                    product_details, product_dir = result
                    # 直接导入该产品（包含图片上传到对象存储）
                    importer.import_product(Path(product_dir))
                    queue_manager.mark_as_completed(product['id'])
                    success_count += 1
                    print(f"✅ 产品处理成功")
                else:
                    raise Exception("产品详情爬取失败")
                    
            except Exception as e:
                print(f"❌ 产品处理失败: {e}")
                queue_manager.add_to_failed_queue(
                    product['url'], 
                    product['product_name'], 
                    str(e)
                )
                queue_manager.mark_as_completed(product['id'])  # 标记为已完成，避免重复处理
                failed_count += 1
        
        # 显示当前统计
        stats = queue_manager.get_queue_stats()
        print(f"\n当前统计: 成功 {success_count}, 失败 {failed_count}")
        print(f"队列状态: 待处理 {stats['pending']}, 处理中 {stats['processing']}, 已完成 {stats['completed']}, 失败 {stats['failed']}")
    
    # 最终统计
    print("\n" + "=" * 50)
    print("=== 处理完成 ===")
    print(f"成功处理: {success_count} 个产品")
    print(f"失败: {failed_count} 个产品")
    
    # 清理已完成的项目
    if success_count > 0:
        queue_manager.clear_completed()

if __name__ == "__main__":
    main()
