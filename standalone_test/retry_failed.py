#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性脚本：重试失败队列中的任务。

用法（可选传参）:
  python retry_failed.py [BRAND_CODE]

说明：
- BRAND_CODE 默认为 HG，可传 MG/RG/PG...
- 成功则从失败队列移除；失败则仅累加重试计数，仍留在失败队列。
"""

import sys
import os
from pathlib import Path

# 确保可导入 src 目录
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from scraper import BandaiScraper
from queue_manager import QueueManager
from database import DatabaseManager
from data_importer import DataImporter
from config import Config


def main():
    brand_code = sys.argv[1] if len(sys.argv) > 1 else 'HG'
    print(f"重试失败队列，品牌: {brand_code}")

    scraper = BandaiScraper()
    queue_manager = QueueManager(Config.DATABASE_PATH)
    importer = DataImporter()

    failed_items = queue_manager.get_failed_products(limit=1000)
    if not failed_items:
        print("失败队列为空，无需重试。")
        return

    print(f"待重试失败任务: {len(failed_items)}")

    success_count = 0
    failed_count = 0

    for item in failed_items:
        failed_id = item['id']
        url = item['url']
        product_name = item['product_name'] or ''
        print(f"\n--- 重试: #{failed_id} {product_name}")
        print(f"URL: {url}")

        try:
            result = scraper.scrape_product_details(
                product_url=url,
                base_dir=f'data/{brand_code}',
                queue_product_name=product_name
            )

            if result:
                _, product_dir = result
                importer.import_product(Path(product_dir))
                queue_manager.remove_failed(failed_id)
                success_count += 1
                print("✅ 重试成功，已从失败队列移除")
            else:
                queue_manager.increment_failed_retry(failed_id)
                failed_count += 1
                print("❌ 重试失败，已累计重试次数")
        except Exception as e:
            queue_manager.increment_failed_retry(failed_id)
            failed_count += 1
            print(f"❌ 重试异常: {e}")

    print("\n=== 重试完成 ===")
    print(f"成功: {success_count}，失败: {failed_count}")


if __name__ == '__main__':
    main()


