#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万代模型爬虫主类
"""

import requests
import json
import os
import time
from typing import List, Optional

from config import (
    PRODUCT_LIST_URL,  DEFAULT_HEADERS, 
    REQUEST_TIMEOUT, SCRAPED_DATA_FILE
)
from models import ProductLink, ProductDetails, ScrapingResult
from page_parser import PageParser
from data_extractor import DataExtractor
from image_downloader import ImageDownloader


class BandaiScraper:
    """万代模型爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        
        # 初始化各个功能模块
        self.page_parser = PageParser(self.session)
        self.data_extractor = DataExtractor()
        self.image_downloader = ImageDownloader(self.session)
    
    
    def get_total_pages(self) -> int:
        """
        获取产品列表的总页数
        
        Returns:
            int: 总页数，获取失败时返回1
        """
        return self.page_parser.get_total_pages()
    
    def scrape_product_list(self, num_pages: int = None, start_page: int = 1) -> ScrapingResult:
        """
        抓取产品列表页面（支持多页）
        
        Args:
            num_pages: 爬取页数，默认为5页
            start_page: 起始页码，默认为1
            
        Returns:
            ScrapingResult: 爬取结果
        """
        result = self.page_parser.scrape_product_list(num_pages, start_page)
        
        # 保存结果到JSON文件
        if result.success and result.data:
            self._save_product_list(result.data)
        
        return result
    
    def scrape_product_details(self, product_url: str = None, output_path: str = None) -> Optional[ProductDetails]:
        """
        抓取产品详情页面
        
        Args:
            product_url: 产品详情页URL，默认使用配置中的URL
            output_path: 产品文件夹路径，用于保存图片和JSON文件
            
        Returns:
            ProductDetails: 产品详情信息，失败时返回None
        """
        url = product_url
        
        # 校验URL格式
        if not url or not url.startswith('https://bandai-hobby.net/item'):
            print(f"❌ 不支持的URL格式: {url}")
            return None
        
        try:
            # 使用页面解析器解析产品页面
            soup = self.page_parser.parse_product_page(url)
            if not soup:
                return None
            
            # 1. 获取产品名称
            product_name = self.data_extractor.extract_product_name(soup)
            safe_folder_name = self.data_extractor.sanitize_folder_name(product_name)
            output_path = os.path.join(output_path, safe_folder_name)
            
            # 检查是否已存在产品文件夹和JSON文件
            json_file_path = os.path.join(output_path, "product_details.json")
            existing_data = None
            
            # 初始化数据
            if os.path.exists(json_file_path):
                print(f"发现已存在的产品文件夹: {output_path}")
                # 读取现有的JSON文件
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = {}
            
            # 1. 处理产品详细信息
            if existing_data.get('product_info') and existing_data['product_info']:
                product_info = existing_data['product_info']
            else:
                product_info = self.data_extractor.extract_product_info(soup)
            
            # 2. 处理产品文章内容
            if existing_data.get('article_content') and existing_data['article_content'].strip():
                article_content = existing_data['article_content']
            else:
                article_content = self.data_extractor.extract_article_content(soup)
            
            # 3. 处理产品标签
            if existing_data.get('product_tag'):
                product_tag = existing_data['product_tag']
            else:
                product_tag = self.data_extractor.extract_product_tag(soup)
            
            # 4. 处理系列链接
            if existing_data.get('series'):
                series = existing_data['series']
            else:
                series = self.data_extractor.extract_series_links(soup)
            
            # 5. 处理图片链接
            if existing_data.get('image_links') and existing_data['image_links']:
                image_links = existing_data['image_links']
            else:
                image_links = self.data_extractor.extract_image_links(soup)
            
            # 更新或创建数据
            existing_data.update({
                'product_name': product_name,
                'product_info': product_info,
                'article_content': article_content,
                'product_tag': product_tag,
                'series': series,
                'image_links': image_links,
                'url': url
            })
            
            # 检查是否需要下载图片
            need_download_images = True
            if image_links:
                images_dir = os.path.join(output_path, "images")
                existing_images = []
                
                if os.path.exists(images_dir):
                    existing_images = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                
                # 比较图片链接数量和实际文件数量
                if len(existing_images) == len(image_links):
                    print(f"✅ 图片已完整下载 ({len(existing_images)}/{len(image_links)})，跳过图片下载")
                    need_download_images = False
                else:
                    print(f"⚠️ 图片不完整 (现有:{len(existing_images)}, 需要:{len(image_links)})，需要下载图片")
            else:
                print(f"ℹ️ 没有图片链接，跳过图片下载")
                need_download_images = False
            
            # 下载图片
            download_success = False
            if need_download_images and image_links:
                downloaded_files, download_success = self.image_downloader.download_images(
                    image_links, url, os.path.join(output_path, "images")
                )
                if download_success:
                    print(f"✅ 图片下载成功，共下载 {len(downloaded_files)} 张图片")
                else:
                    print(f"❌ 图片下载失败")
            else:
                download_success = True
            
            # 创建产品详情对象
            product_details = ProductDetails(
                name=product_name,
                image_links=image_links,
                product_info=product_info,
                article_content=article_content,
                url=url,
                product_tag=product_tag,
                series=series
            )
            
            # 保存结果
            self._save_product_details(product_details, output_path)
            
            return product_details
            
        except Exception as e:
            print(f"处理产品详情时出错: {e}")
            return None
    
    
    def _save_product_list(self, results: List[ProductLink]):
        """保存产品列表到文件"""
        # 转换为可序列化的格式
        data = []
        for result in results:
            data.append({
                'href': result.href,
                'text': result.text,
            })
        
        with open(SCRAPED_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"产品列表已保存到: {SCRAPED_DATA_FILE}")
    
    def _save_product_details(self, product_details: ProductDetails, output_path: str = None):
        """保存产品详情到文件"""
        if output_path:
            # 确保文件夹存在
            os.makedirs(output_path, exist_ok=True)
            # 保存到产品文件夹
            file_path = os.path.join(output_path, "product_details.json")
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(product_details.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"产品详情已保存到: {file_path}")

    def test_scrape_product_list(self):
        """测试产品列表爬取功能"""
        print("\n" + "="*60)
        print("测试: 产品列表爬取")
        print("="*60)
        
        result = self.scrape_product_list()
        
        if result.success:
            print("\n✅ 测试通过！")
            print(f"   成功获取 {len(result.data)} 个产品链接")
            for i, link in enumerate(result.data[:3], 1):
                print(f"   {i}. {link.text}")
            if len(result.data) > 3:
                print(f"   ... 共 {len(result.data)} 个产品")
        else:
            print("\n❌ 测试失败！")
            print(f"   错误: {result.error_message}")
        
        return result

if __name__ == "__main__":
    # 直接运行测试
    scraper = BandaiScraper()
    result = scraper.scrape_product_list()
    if result.success:
        print("\n✅ 测试通过！")
        print(f"   成功获取 {len(result.data)} 个产品链接")
        for i, link in enumerate(result.data[:3], 1):
            print(f"   {i}. {link.text}")
        if len(result.data) > 3:
            print(f"   ... 共 {len(result.data)} 个产品")
    else:
        print("\n❌ 测试失败！")
        print(f"   错误: {result.error_message}")
