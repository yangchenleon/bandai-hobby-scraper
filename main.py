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



def main():
    """
    主函数
    """
    print("万代模型爬虫启动...")
    print("=" * 50)
    
    # 创建爬虫实例和队列管理器
    scraper = BandaiScraper()
    from queue_manager import QueueManager
    from config import Config
    
    queue_manager = QueueManager(Config.DATABASE_PATH)
    
    # 重置处理中的任务为待处理状态
    print("=== 检查并重置处理中的任务 ===")
    queue_manager.reset_processing_to_pending()
    
    # 配置参数
    start_page = 1
    batch_size = 10
    brand_code = "MGEX"  # 使用大写品牌代码
    from config import BRAND_CODE_TO_SLUG
    brand_slug = BRAND_CODE_TO_SLUG.get(brand_code)
    base_url = PRODUCT_LIST_URL + brand_slug + '/'
    end_page = scraper.get_total_pages(base_url)
    
    # 1. 爬取产品列表并添加到待处理队列
    print(f"=== 爬取产品列表（第 {start_page} 到 {end_page} 页） ===")
    for page_num in range(start_page, end_page + 1):
        print(f"\n正在爬取第 {page_num} 页...")
        list_result = scraper.scrape_product_list(num_pages=1, start_page=page_num, base_url=base_url, brand_code=brand_code)
        
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
                    base_dir=f'data/{brand_code}',
                    queue_product_name=product['product_name']
                )
                
                if result:
                    product_details, product_dir = result
                    # 详情已保存至本地文件夹
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
