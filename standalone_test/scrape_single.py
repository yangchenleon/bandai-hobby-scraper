#!/home/chen/miniconda3/envs/unibase2/bin/python
# -*- coding: utf-8 -*-
"""
单产品强制抓取脚本
给定一个产品URL，查看队列状态，并强制重新抓取（完全覆盖原有文件夹数据）

用法:
    python scrape_single.py <URL> [--brand <品牌代码>]
示例:
    python scrape_single.py https://bandai-hobby.net/item/5937/ --brand HG
"""

import sys
import os
import sqlite3
import shutil
import argparse

# 确保可导入 src 目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import urllib.parse
from bs4 import BeautifulSoup
from config import Config, BRAND_CODE_TO_SLUG
from queue_manager import QueueManager
from scraper import BandaiScraper


def find_avatar_from_list(scraper, brand_code, series, tags, target_url):
    """
    通过列表页过滤条件倒查商品的头像和基础信息
    """
    base_url = "https://bandai-hobby.net"
    search_url = ""
    params = {'p': 1, 'sort': '', 'title': ''}
    
    # 优先使用品牌查找（通常商品都在对应的品牌下）
    brand_slug = BRAND_CODE_TO_SLUG.get(brand_code)
    if brand_slug:
        search_url = f"{base_url}/brand/{brand_slug}/"
    elif series:
        # 退而求其次使用系列
        # series 可能是多个用分号分割，取第一个
        first_series = series.split(';')[0] if isinstance(series, str) else series
        search_url = f"{base_url}/series/{first_series}/"
        params['code'] = first_series
    else:
        return None
        
    # 添加tag过滤
    if tags:
        tag_list = tags.split(';') if isinstance(tags, str) else tags
        # requests 库的 params 参数不支持同名 key 传递列表（会变成 order_form=a&order_form=b），
        # 我们手动构造 query string 或传 list
        params['order_form'] = tag_list

    print(f"   [倒查列表页] 搜索URL: {search_url} 参数: {params}")
    
    # 限制最多搜索前 5 页
    for page in range(1, 6):
        params['p'] = page
        try:
            res = scraper.session.get(search_url, params=params, headers={'User-Agent': scraper._get_random_ua()})
            if res.status_code != 200:
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            cards = soup.find_all('a', href=lambda x: x and '/item/' in x)
            
            if not cards:
                break
                
            for card in cards:
                href = card.get('href')
                full_url = urllib.parse.urljoin(base_url, href)
                
                # 检查是否匹配目标URL
                if target_url in full_url or full_url in target_url:
                    img_tag = card.select_one('img')
                    if img_tag and img_tag.get('src'):
                        avatar_url = img_tag.get('src')
                        print(f"   ✅ 在第 {page} 页找到对应商品，提取到头像: {avatar_url}")
                        return avatar_url
                        
        except Exception as e:
            print(f"   [倒查列表页] 搜索时发生错误: {e}")
            break
            
    print("   ❌ 在列表页中未找到对应的商品信息")
    return None


def get_url_status(db_path, url):
    """查询URL在队列中的状态"""
    if not os.path.exists(db_path):
        return None
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, product_name, status FROM pending_queue WHERE url = ?', (url,))
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()
        
    if row:
        return {"id": row[0], "product_name": row[1], "status": row[2]}
    return None


def main():
    parser = argparse.ArgumentParser(description="单个产品强制抓取脚本")
    parser.add_argument("url", help="产品的URL")
    parser.add_argument("--brand", default="HG", help="品牌代码，如 HG, MG (默认: HG)")
    parser.add_argument("--no-delete", action="store_true", help="不删除原有文件夹（默认会强制删除以实现完全覆盖）")
    
    args = parser.parse_args()
    
    url = args.url
    brand_code = args.brand.upper()
    
    print("=" * 60)
    print(f"开始处理单个产品: {url}")
    print(f"品牌代码: {brand_code}")
    print("=" * 60)
    
    # 初始化组件
    queue_manager = QueueManager(Config.DATABASE_PATH)
    scraper = BandaiScraper()
    
    # 1. 检查队列状态
    status_info = get_url_status(Config.DATABASE_PATH, url)
    
    product_name = "manual_scrape_item"
    queue_id = None
    
    if status_info:
        print(f"✅ 在队列中找到该URL记录:")
        print(f"   - 队列ID: {status_info['id']}")
        print(f"   - 产品名称: {status_info['product_name']}")
        print(f"   - 当前状态: {status_info['status']}")
        product_name = status_info['product_name'] or product_name
        queue_id = status_info['id']
        
        # 将状态标记为处理中
        queue_manager.mark_as_processing(queue_id)
    else:
        print(f"⚠️ 在队列中未找到该URL，将作为新任务处理")
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pending_queue (url, product_name, status)
            VALUES (?, ?, 'processing')
        ''', (url, product_name))
        queue_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"   - 已创建新队列记录，ID: {queue_id}")
        
    # 2. 清理原有文件夹以实现完全覆盖
    base_dir = os.path.join(PROJECT_ROOT, f'data/{brand_code}')
    
    if not args.no_delete:
        # 获取预测的文件夹名称
        product_id = scraper.data_extractor.extract_product_id(url)
        safe_folder_name = scraper.data_extractor.sanitize_folder_name(product_name)
        folder_name = f"{product_id}_{safe_folder_name}" if product_id else safe_folder_name
        
        target_folder = os.path.join(base_dir, folder_name)
        old_path = os.path.join(base_dir, safe_folder_name)
        
        deleted = False
        if os.path.exists(target_folder):
            print(f"🗑️ 发现已存在的数据文件夹，正在删除以完全覆盖: {target_folder}")
            shutil.rmtree(target_folder)
            deleted = True
        elif os.path.exists(old_path):
            print(f"🗑️ 发现已存在的旧格式数据文件夹，正在删除以完全覆盖: {old_path}")
            shutil.rmtree(old_path)
            deleted = True
            
        if not deleted:
            print(f"ℹ️ 未发现已存在的数据文件夹，将直接创建新文件夹")
    else:
        print(f"ℹ️ 已指定 --no-delete，将以增量/合并模式更新原有数据")
        
    # 3. 爬取
    print(f"\n--- 开始抓取详情页 ---")
    try:
        result = scraper.scrape_product_details(
            product_url=url,
            base_dir=base_dir,
            queue_product_name=product_name
        )
        
        if result:
            product_details, product_dir = result
            print(f"\n✅ 详情页抓取成功！")
            print(f"   - 详情保存在: {product_dir}")
            print(f"   - 产品名称: {product_details.name}")
            
            # 4. 倒序补全列表页信息（头像等）
            print(f"\n--- 开始倒查列表页补全信息 ---")
            tags = product_details.product_tag
            series = product_details.series
            
            avatar_url = find_avatar_from_list(scraper, brand_code, series, tags, url)
            if avatar_url:
                product_details.avatar = avatar_url
                
                # 下载头像
                print("   正在下载头像...")
                scraper.image_downloader.download_single_image(
                    image_url=avatar_url,
                    referer_url=url,
                    output_path=product_dir
                )
                
                # 重新保存更新后的 json
                scraper._save_product_details(product_details, product_dir)
            
            # 标记为已完成
            if queue_id:
                queue_manager.mark_as_completed(queue_id)
                # 尝试清理失败队列记录（如果有）
                conn = sqlite3.connect(Config.DATABASE_PATH)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM failed_queue WHERE url = ?', (url,))
                conn.commit()
                conn.close()
        else:
            print(f"\n❌ 抓取失败，未返回结果。")
            if queue_id:
                queue_manager.mark_as_failed_in_pending(queue_id)
                queue_manager.add_to_failed_queue(url, product_name, "单体抓取未返回结果")
            
    except Exception as e:
        print(f"\n❌ 抓取过程中发生异常: {e}")
        if queue_id:
            queue_manager.mark_as_failed_in_pending(queue_id)
            queue_manager.add_to_failed_queue(url, product_name, str(e))


if __name__ == "__main__":
    main()
