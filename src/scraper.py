#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万代模型爬虫主类
"""

import requests
import json
import os
import time
from urllib.parse import urlparse
from typing import List, Optional, Tuple

from config import (
    PRODUCT_LIST_URL,  DEFAULT_HEADERS, 
    REQUEST_TIMEOUT, SCRAPED_DATA_FILE, CSS_SELECTORS, BRAND_CODE_TO_SLUG
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
    
    
    def get_total_pages(self, base_url: Optional[str] = None) -> int:
        """
        获取产品列表的总页数
        
        Returns:
            int: 总页数，获取失败时返回1
        """
        try:
            target_url = base_url or PRODUCT_LIST_URL
            print(f"正在获取总页数: {target_url}")
            response = self.session.get(target_url, timeout=REQUEST_TIMEOUT)
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
    
    def scrape_product_list(self, num_pages: int = None, start_page: int = 1, base_url: str = None, brand_code: str = None) -> ScrapingResult:
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
                    
                    # 精确提取产品信息
                    product_name = ""
                    product_price = ""
                    product_release_date = ""
                    
                    # 提取产品名称
                    title_elem = link.select_one('.p-card__tit')
                    if title_elem:
                        product_name = title_elem.get_text(strip=True)
                    
                    # 提取价格
                    price_elem = link.select_one('.p-card__price')
                    if price_elem:
                        product_price = price_elem.get_text(strip=True)
                    
                    # 提取发布日期
                    date_elem = link.select_one('.p-card_date')
                    if date_elem:
                        product_release_date = date_elem.get_text(strip=True)
                    
                    # 组合完整的产品信息
                    # link_text = f"{product_name}-{product_price}-{product_release_date}"
                    print(f"产品信息: {product_name} | {product_price} | {product_release_date}")

                    # 查找列表头像图（p-card__img 下的 img）
                    avatar_url = None
                    img_tag = link.select_one('.p-card__img img')
                    if img_tag and img_tag.get('src'):
                        avatar_url = img_tag.get('src')

                    # 创建产品链接对象（附带 avatar 链接）
                    product_link = ProductLink(
                        href=href,
                        text=product_name,
                        avatar=avatar_url
                    )
                    page_results.append(product_link)


                    # 若有头像，下载到产品根目录，并将下载链接写入产品JSON的 avatar 字段
                    try:
                        if avatar_url and href:
                            # 生成产品目录（基于产品名文本）
                            safe_folder_name = self.data_extractor.sanitize_folder_name(product_name or 'product')
                            # 若传入品牌代码，则在 data/<BRAND>/ 下保存
                            brand_folder = None
                            if brand_code and BRAND_CODE_TO_SLUG.get(brand_code.upper()):
                                brand_folder = brand_code.upper()
                            product_dir = os.path.join('data', brand_folder, safe_folder_name) if brand_folder else os.path.join('data', safe_folder_name)
                            os.makedirs(product_dir, exist_ok=True)

                            # 通过图片下载器下载（Referer 使用当前列表页 URL）
                            # 若头像已存在则跳过下载
                            avatar_filename = os.path.basename(urlparse(avatar_url).path)
                            target_avatar_path = os.path.join(product_dir, avatar_filename) if avatar_filename else None
                            if target_avatar_path and os.path.exists(target_avatar_path):
                                saved_path = target_avatar_path
                            else:
                                saved_path = self.image_downloader.download_single_image(
                                    image_url=avatar_url,
                                    referer_url=current_url,
                                    output_path=product_dir
                                )

                            # 将 avatar 链接写入/更新产品 JSON（与后续详情逻辑兼容）
                            json_path = os.path.join(product_dir, 'product_details.json')
                            existing = {}
                            if os.path.exists(json_path):
                                try:
                                    with open(json_path, 'r', encoding='utf-8') as f:
                                        existing = json.load(f)
                                except Exception:
                                    existing = {}

                            # 最小字段填充，详情阶段会覆盖/补全
                            existing.setdefault('product_name', product_name)
                            existing.setdefault('product_info', {
                                '価格': product_price, 
                                '発売日': product_release_date,
                                '対象年齢': '8歳以上'
                            })
                            existing.setdefault('article_content', '')
                            existing.setdefault('image_links', [])
                            existing.setdefault('product_tag', '')
                            existing.setdefault('series', '')
                            existing['url'] = href
                            existing['avatar'] = avatar_url

                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(existing, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"  列表头像处理失败: {e}")
                
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
    
    def scrape_product_details(self, product_url: str, base_dir: str, queue_product_name: str) -> Optional[Tuple[ProductDetails, str]]:
        """
        抓取产品详情页面
        
        Args:
            product_url: 产品详情页URL
            base_dir: 基础目录路径（如 'data'）
            queue_product_name: 队列中的产品名称，用于确定最终路径
            
        Returns:
            Tuple[ProductDetails, str]: (产品详情信息, 产品文件夹路径)，失败时返回None
        """
        url = product_url
        
        # Premium Bandai 特殊页面处理
        if url and 'p-bandai' in url:
            return self._scrape_p_bandai_details(url, base_dir, queue_product_name)
        
        # 常规bandai-hobby页面
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
            
            # 构建产品文件夹路径
            safe_folder_name = self.data_extractor.sanitize_folder_name(queue_product_name)
            target_folder = os.path.join(base_dir, safe_folder_name)
            
            if os.path.exists(target_folder):
                output_path = target_folder
                print(f"找到对应文件夹: {output_path}")
            else:
                # 如果没找到，使用解析的产品名称创建新文件夹
                safe_folder_name = self.data_extractor.sanitize_folder_name(product_name)
                output_path = os.path.join(base_dir, safe_folder_name)
                print(f"未找到对应文件夹，使用解析的产品名称: {output_path}")
            
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
            product_info = self.data_extractor.extract_product_info(soup)
            
            # 2. 处理产品文章内容
            article_content = self.data_extractor.extract_article_content(soup)
            
            # 3. 处理产品标签
            product_tag = self.data_extractor.extract_product_tag(soup)
            
            # 4. 处理系列链接
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
                    raise Exception("图片下载失败，任务失败")
            else:
                download_success = True
            
            # 创建产品详情对象（保留已存在的 avatar）
            existing_avatar = existing_data.get('avatar', '') if isinstance(existing_data, dict) else ''
            # 从base_dir中提取brand信息 (data/HG -> HG)
            brand = os.path.basename(base_dir) if base_dir else ""
            product_details = ProductDetails(
                name=product_name,
                image_links=image_links,
                product_info=product_info,
                article_content=article_content,
                url=url,
                product_tag=product_tag,
                series=series,
                avatar=existing_avatar,
                brand=brand
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

    def _scrape_p_bandai_details(self, url: str, base_dir: str, product_name: Optional[str]) -> Optional[Tuple[ProductDetails, str]]:
        """处理 Premium Bandai 商品页，基于待处理队列的产品名拆分信息。"""
        try:

            # 请求页面，提取正文
            print(f"正在访问Premium Bandai产品详情页: {url}")
            print("爬不了一点，过")
            # response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            # response.raise_for_status()
            # response.encoding = 'utf-8'
            # soup = BeautifulSoup(response.text, 'html.parser')

            # article_section = soup.find(class_='item_caption_area')
            # if article_section:
            #     article_content = BeautifulSoup(str(article_section), 'html.parser').get_text(separator='\n', strip=False)
            # else:
            #     print("未找到 item_caption_area，文章内容置空")
            #     article_content = ""

            # 固定标签
            product_tag = "premium"
            series = "gunpla"

            # 构建产品文件夹路径
            safe_folder_name = self.data_extractor.sanitize_folder_name(product_name or "premium_item")
            output_path = os.path.join(base_dir, safe_folder_name)
            print(f"使用解析的产品名称: {output_path}")

            # Premium站点暂不处理图片下载（可后续扩展）
            image_links: List[str] = []

            # 读取已存在的数据（如有）
            existing_avatar = ''
            existing_name = product_name
            existing_info = ""  # Premium Bandai 暂不处理产品信息
            json_path = os.path.join(output_path, 'product_details.json')
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    if isinstance(existing_data, dict):
                        existing_avatar = existing_data.get('avatar', '')
                        existing_name = existing_data.get('name', product_name)
                        existing_info = existing_data.get('product_info', "")
                except Exception:
                    existing_avatar = ''

            # 从base_dir中提取brand信息 (data/HG -> HG)
            brand = os.path.basename(base_dir) if base_dir else ""
            details = ProductDetails(
                name=existing_name,
                image_links=image_links,
                product_info=existing_info,
                article_content="",
                url=url,
                product_tag=product_tag,
                series=series,
                avatar=existing_avatar,
                brand=brand
            )

            # 保存JSON
            self._save_product_details(details, output_path)
            return details, output_path

        except requests.exceptions.RequestException as e:
            print(f"请求Premium Bandai页面时出错: {e}")
            return None
        except Exception as e:
            print(f"处理Premium Bandai详情时出错: {e}")
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
