#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万代模型爬虫主类
"""

import requests
import json
import os
import time
from typing import List, Optional, Tuple

from config import (
    PRODUCT_LIST_URL,  DEFAULT_HEADERS, 
    REQUEST_TIMEOUT, SCRAPED_DATA_FILE, CSS_SELECTORS
)
from models import ProductLink, ProductDetails, ScrapingResult
from data_extractor import DataExtractor
from image_downloader import ImageDownloader
from bs4 import BeautifulSoup


class BandaiScraper:
    """万代模型爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
    
        # 初始化各个功能模块
        self.data_extractor = DataExtractor()
        self.image_downloader = ImageDownloader(self.session)
    
    
    def get_total_pages(self) -> int:
        """
        获取产品列表的总页数
        
        Returns:
            int: 总页数，获取失败时返回1
        """
        try:
            print(f"正在获取总页数: {PRODUCT_LIST_URL}")
            response = self.session.get(PRODUCT_LIST_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找分页链接
            pagination_links = soup.find_all(class_=CSS_SELECTORS['pagination_links'])
            print(f"找到 {len(pagination_links)} 个分页链接")
            
            if not pagination_links:
                print("未找到分页链接，返回默认页数1")
                return 1
            
            # 获取最后一个分页链接的页码
            last_link = pagination_links[-1]
            page_text = last_link.get_text(strip=True)
            
            # 尝试提取页码数字
            try:
                total_pages = int(page_text)
                print(f"总页数: {total_pages}")
                return total_pages
            except ValueError:
                # 如果无法转换为数字，尝试从href中提取
                href = last_link.get('href', '')
                if 'p=' in href:
                    # 从URL参数中提取页码
                    import re
                    match = re.search(r'p=(\d+)', href)
                    if match:
                        total_pages = int(match.group(1))
                        print(f"从URL中提取总页数: {total_pages}")
                        return total_pages
                
                print(f"无法解析页码 '{page_text}'，返回默认页数1")
                return 1
                
        except requests.exceptions.RequestException as e:
            print(f"获取总页数时请求错误: {e}")
            return 1
        except Exception as e:
            print(f"获取总页数时出错: {e}")
            return 1
    
    def scrape_product_list(self, num_pages: int = None, start_page: int = 1, base_url: str = None) -> ScrapingResult:
        """
        抓取产品列表页面（支持多页）
        
        Args:
            num_pages: 爬取页数，默认为5页
            start_page: 起始页码，默认为1
            
        Returns:
            ScrapingResult: 爬取结果
        """
        if base_url is None:
            print("❌ 未提供基础URL")
            return ScrapingResult(success=False, error_message="未提供基础URL")
        try:
            all_results = []
            page = start_page
            max_pages = start_page + num_pages - 1

            while page <= max_pages:
                # 构建当前页URL
                if page == 1:
                    current_url = base_url
                else:
                    current_url = f"{base_url}?p={page}"
                
                print(f"\n正在访问第 {page} 页: {current_url}")
                response = self.session.get(current_url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                print(f"响应状态码: {response.status_code}")
                print(f"响应内容长度: {len(response.text)} 字符")
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找指定class的元素
                target_elements = soup.find_all(class_=CSS_SELECTORS['product_cards'])
                print(f"找到 {len(target_elements)} 个匹配的元素")
                
                if not target_elements:
                    print(f"第 {page} 页未找到产品卡片，可能已到最后一页")
                    break
                
                page_results = []
                element = target_elements[0]  # 只处理第一个元素
                
                # 查找所有链接
                links = element.find_all('a')
                print(f"找到 {len(links)} 个链接")
                
                for link in links:
                    href = link.get('href')
                    # 有些链接包含多个文本片段，使用 '-' 进行分隔
                    link_text = '-'.join(s for s in link.stripped_strings if s)
                    
                    # 创建产品链接对象
                    product_link = ProductLink(
                        href=href,
                        text=link_text,
                    )
                    page_results.append(product_link)
                    
                    print(f"  链接: {link_text} -> {href}")
                
                print(f"第 {page} 页收集到 {len(page_results)} 个产品链接")
                all_results.extend(page_results)
                
                # 如果当前页没有产品，说明已到最后一页
                if not page_results:
                    print(f"第 {page} 页没有产品，停止爬取")
                    break
                
                page += 1
                
                # 添加延迟避免请求过于频繁
                time.sleep(1)
            
            print(f"\n总共收集到 {len(all_results)} 个产品链接（共 {page-1} 页）")
            
            # 保存结果到JSON文件
            # if all_results:
            #     self._save_product_list(all_results)
            
            return ScrapingResult(success=True, data=all_results)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {e}"
            print(error_msg)
            return ScrapingResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"解析错误: {e}"
            print(error_msg)
            return ScrapingResult(success=False, error_message=error_msg)
    
    def scrape_product_details(self, product_url: str = None, output_path: str = None) -> Optional[Tuple[ProductDetails, str]]:
        """
        抓取产品详情页面
        
        Args:
            product_url: 产品详情页URL，默认使用配置中的URL
            output_path: 产品文件夹路径，用于保存图片和JSON文件
            
        Returns:
            Tuple[ProductDetails, str]: (产品详情信息, 产品文件夹路径)，失败时返回None
        """
        url = product_url
        
        # 校验URL格式
        if not url or not url.startswith('https://bandai-hobby.net/item'):
            print(f"❌ 不支持的URL格式: {url}")
            return None
        
        try:
            # 解析产品页面
            print(f"正在访问产品详情页: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容长度: {len(response.text)} 字符")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
            if existing_data.get('product_tag') and existing_data['product_tag'].strip():
                product_tag = existing_data['product_tag']
            else:
                product_tag = self.data_extractor.extract_product_tag(soup)
            
            # 4. 处理系列链接
            if existing_data.get('series') and existing_data['series'].strip():
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
            
            return product_details, output_path
            
        except requests.exceptions.RequestException as e:
            print(f"请求产品页面时出错: {e}")
            return None
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
