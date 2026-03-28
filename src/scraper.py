#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万代模型爬虫主类
"""

import requests
import json
import os
import time
import random
import logging
from urllib.parse import urlparse
from typing import List, Optional, Tuple

# 第三方库
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from config import (
    PRODUCT_LIST_URL, DEFAULT_HEADERS, 
    REQUEST_TIMEOUT, SCRAPED_DATA_FILE, CSS_SELECTORS, BRAND_CODE_TO_SLUG,
    LOG_DIR, LOG_FILE, LOG_FORMAT, DATE_FORMAT
)
from models import ProductLink, ProductDetails, ScrapingResult
from data_extractor import DataExtractor
from image_downloader import ImageDownloader

# --- 日志配置 ---
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BandaiScraper")

class BandaiScraper:
    """万代模型爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        
        # 初始化 UserAgent
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.warning(f"UserAgent 初始化失败，将使用默认 User-Agent: {e}")
            self.ua = None
    
        # 初始化各个功能模块
        self.data_extractor = DataExtractor()
        self.image_downloader = ImageDownloader(self.session)

    def _get_random_ua(self) -> str:
        """获取随机 User-Agent"""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
        return DEFAULT_HEADERS.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    # 定义重试策略：捕获 RequestException，重试3次（共4次尝试），间隔指数增长 (2s, 4s, 8s...)
    @retry(
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout)),
        stop=stop_after_attempt(4), 
        wait=wait_exponential(multiplier=2, min=2, max=20),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _get_request(self, url: str) -> requests.Response:
        """
        统一的 GET 请求方法，包含重试机制和 UA 轮询
        """
        # 每次请求前更新 User-Agent
        current_ua = self._get_random_ua()
        self.session.headers.update({'User-Agent': current_ua})
        
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            
            # 对 5xx 错误抛出异常以触发重试
            if response.status_code >= 500:
                logger.warning(f"服务器错误 {response.status_code}: {url}")
                response.raise_for_status()
                
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response
            
        except requests.exceptions.HTTPError as e:
            # 4xx 错误通常不重试（除非是 429 Too Many Requests，这里暂不处理）
            if 400 <= e.response.status_code < 500:
                logger.error(f"客户端错误 {e.response.status_code}，不重试: {url}")
                raise e # 直接抛出，不触发 retry
            raise e # 5xx 错误继续抛出，触发 retry
    
    def get_total_pages(self, base_url: Optional[str] = None) -> int:
        """
        获取产品列表的总页数
        """
        try:
            target_url = base_url or PRODUCT_LIST_URL
            logger.info(f"正在获取总页数: {target_url}")
            
            response = self._get_request(target_url)
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找分页链接
            pagination_links = soup.find_all(class_=CSS_SELECTORS['pagination_links'])
            logger.info(f"找到 {len(pagination_links)} 个分页链接")
            
            if not pagination_links:
                logger.info("未找到分页链接，返回默认页数1")
                return 1
            
            # 获取最后一个分页链接的页码
            last_link = pagination_links[-1]
            page_text = last_link.get_text(strip=True)
            
            # 尝试提取页码数字
            try:
                total_pages = int(page_text)
                logger.info(f"总页数: {total_pages}")
                return total_pages
            except ValueError:
                # 如果无法转换为数字，尝试从href中提取
                href = last_link.get('href', '')
                if 'p=' in href:
                    import re
                    match = re.search(r'p=(\d+)', href)
                    if match:
                        total_pages = int(match.group(1))
                        logger.info(f"从URL中提取总页数: {total_pages}")
                        return total_pages
                
                logger.warning(f"无法解析页码 '{page_text}'，返回默认页数1")
                return 1
                
        except Exception as e:
            logger.error(f"获取总页数时出错: {e}")
            return 1
    
    def scrape_product_list(self, num_pages: int = None, start_page: int = 1, base_url: str = None, brand_code: str = None) -> ScrapingResult:
        """
        抓取产品列表页面（支持多页）
        """
        if base_url is None:
            logger.error("未提供基础URL")
            return ScrapingResult(success=False, error_message="未提供基础URL")
        try:
            all_results = []
            page = start_page
            # 如果 num_pages 未指定，这里需要逻辑处理，暂且假设调用方处理或只爬1页
            # 如果 num_pages 为 None, 这里的逻辑可能会有问题，建议调用前确定 num_pages
            # 此处保持原逻辑，注意 max_pages 计算
            loop_pages = num_pages if num_pages else 1
            max_pages = start_page + loop_pages - 1

            while page <= max_pages:
                # 构建当前页URL
                if page == 1:
                    current_url = base_url
                else:
                    current_url = f"{base_url}?p={page}"
                
                logger.info(f"正在访问第 {page} 页: {current_url}")
                
                try:
                    response = self._get_request(current_url)
                except Exception as e:
                    logger.error(f"第 {page} 页请求失败，跳过: {e}")
                    page += 1
                    continue

                logger.debug(f"响应状态码: {response.status_code}, 内容长度: {len(response.text)}")
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找指定class的元素
                target_elements = soup.find_all(class_=CSS_SELECTORS['product_cards'])
                logger.info(f"找到 {len(target_elements)} 个匹配的元素")
                
                if not target_elements:
                    logger.info(f"第 {page} 页未找到产品卡片，可能已到最后一页")
                    break
                
                page_results = []
                element = target_elements[0]  # 只处理第一个元素
                
                # 查找所有链接
                links = element.find_all('a')
                logger.info(f"找到 {len(links)} 个链接")
                
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
                    
                    logger.debug(f"产品信息: {product_name} | {product_price} | {product_release_date}")

                    # 查找列表头像图
                    avatar_url = None
                    img_tag = link.select_one('.p-card__img img')
                    if img_tag and img_tag.get('src'):
                        avatar_url = img_tag.get('src')

                    # 创建产品链接对象
                    product_link = ProductLink(
                        href=href,
                        text=product_name,
                        avatar=avatar_url
                    )
                    page_results.append(product_link)

                    # --- 下载列表头像 (保持原有逻辑) ---
                    try:
                        if avatar_url and href:
                            safe_folder_name = self.data_extractor.sanitize_folder_name(product_name or 'product')
                            brand_folder = None
                            if brand_code and BRAND_CODE_TO_SLUG.get(brand_code.upper()):
                                brand_folder = brand_code.upper()
                            product_dir = os.path.join('data', brand_folder, safe_folder_name) if brand_folder else os.path.join('data', safe_folder_name)
                            os.makedirs(product_dir, exist_ok=True)

                            avatar_filename = os.path.basename(urlparse(avatar_url).path)
                            target_avatar_path = os.path.join(product_dir, avatar_filename) if avatar_filename else None
                            
                            # 头像下载也应该包含在重试逻辑中吗？ImageDownloader 内部应自行处理，这里仅调用
                            if target_avatar_path and os.path.exists(target_avatar_path):
                                pass
                            else:
                                # 注意：ImageDownloader 需要能够处理 Session，这里复用 self.session (已包含随机UA逻辑吗？
                                # self.session 在 _get_request 中更新了 header，这里直接使用 session 下载时
                                # 建议手动更新一次 UserAgent 以防万一，或者 ImageDownloader 内部处理
                                self.image_downloader.download_single_image(
                                    image_url=avatar_url,
                                    referer_url=current_url,
                                    output_path=product_dir
                                )

                            # 写入简略 JSON (使用智能合并)
                            json_path = os.path.join(product_dir, 'product_details.json')
                            old_data = {}
                            if os.path.exists(json_path):
                                try:
                                    with open(json_path, 'r', encoding='utf-8') as f:
                                        old_data = json.load(f)
                                except Exception:
                                    old_data = {}

                            new_data = {
                                'product_name': product_name,
                                'product_info': {
                                    '価格': product_price, 
                                    '発売日': product_release_date,
                                    '対象年齢': '8歳以上'
                                },
                                'article_content': '',
                                'image_links': [],
                                'product_tag': '',
                                'series': '',
                                'url': href,
                                'avatar': avatar_url
                            }
                            
                            merged_data = self._smart_merge(old_data, new_data)

                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(merged_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.warning(f"列表头像处理失败 [{product_name}]: {e}")
                
                logger.info(f"第 {page} 页收集到 {len(page_results)} 个产品链接")
                all_results.extend(page_results)
                
                if not page_results:
                    logger.info(f"第 {page} 页没有产品，停止爬取")
                    break
                
                page += 1
                
                # --- 随机延时 ---
                sleep_time = random.uniform(1.5, 3.5)
                logger.info(f"页面抓取完成，随机延时 {sleep_time:.2f} 秒...")
                time.sleep(sleep_time)
            
            logger.info(f"总共收集到 {len(all_results)} 个产品链接（共 {page-start_page} 页）")
            
            return ScrapingResult(success=True, data=all_results)
            
        except Exception as e:
            error_msg = f"解析错误: {e}"
            logger.critical(error_msg, exc_info=True)
            return ScrapingResult(success=False, error_message=error_msg)
    
    def scrape_product_details(self, product_url: str, base_dir: str, queue_product_name: str) -> Optional[Tuple[ProductDetails, str]]:
        """
        抓取产品详情页面
        """
        url = product_url
        
        # Premium Bandai 特殊页面处理
        if url and 'p-bandai' in url:
            return self._scrape_p_bandai_details(url, base_dir, queue_product_name)
        
        # 常规bandai-hobby页面
        if not url or not url.startswith('https://bandai-hobby.net/item'):
            logger.error(f"不支持的URL格式: {url}")
            return None
        
        try:
            # 解析产品页面
            logger.info(f"正在访问产品详情页: {url}")
            
            # 使用带重试的请求方法
            response = self._get_request(url)
            
            logger.debug(f"响应状态码: {response.status_code}")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. 获取产品名称和ID
            product_name = self.data_extractor.extract_product_name(soup)
            product_id = self.data_extractor.extract_product_id(url)
            
            # 构建产品文件夹路径
            safe_folder_name = self.data_extractor.sanitize_folder_name(queue_product_name)
            
            if product_id:
                folder_name = f"{product_id}_{safe_folder_name}"
            else:
                folder_name = safe_folder_name
                
            target_folder = os.path.join(base_dir, folder_name)
            
            # 文件夹处理逻辑 (迁移旧文件夹等)
            if os.path.exists(target_folder):
                output_path = target_folder
                logger.debug(f"找到对应文件夹: {output_path}")
            else:
                old_path = os.path.join(base_dir, safe_folder_name)
                if os.path.exists(old_path) and product_id:
                    logger.info(f"发现旧格式文件夹: {old_path}，将迁移到新格式: {target_folder}")
                    try:
                        os.rename(old_path, target_folder)
                        output_path = target_folder
                    except Exception as e:
                        logger.error(f"迁移文件夹失败: {e}，将创建新文件夹")
                        output_path = target_folder
                else:
                    output_path = target_folder
                    logger.debug(f"创建新产品文件夹: {output_path}")
            
            # 检查是否已存在产品文件夹和JSON文件
            json_file_path = os.path.join(output_path, "product_details.json")
            existing_data = None
            
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = {}
            
            # 提取各项信息
            product_info = self.data_extractor.extract_product_info(soup)
            article_content = self.data_extractor.extract_article_content(soup)
            product_tag = self.data_extractor.extract_product_tag(soup)
            series = self.data_extractor.extract_series_links(soup)
            
            if existing_data.get('image_links') and existing_data['image_links']:
                image_links = existing_data['image_links']
            else:
                image_links = self.data_extractor.extract_image_links(soup)
            
            # 更新数据字典
            existing_data.update({
                'product_name': product_name,
                'product_info': product_info,
                'article_content': article_content,
                'product_tag': product_tag,
                'series': series,
                'image_links': image_links,
                'url': url
            })
            
            # 图片下载逻辑
            need_download_images = True
            if image_links:
                images_dir = os.path.join(output_path, "images")
                existing_images = []
                if os.path.exists(images_dir):
                    existing_images = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                
                if len(existing_images) == len(image_links):
                    logger.info(f"图片已完整下载 ({len(existing_images)}/{len(image_links)})，跳过")
                    need_download_images = False
                else:
                    logger.info(f"图片不完整 (现有:{len(existing_images)}, 需要:{len(image_links)})，需要下载")
            else:
                logger.info(f"没有图片链接，跳过图片下载")
                need_download_images = False
            
            if need_download_images and image_links:
                # 传入 session 供 downloader 使用 (Session 已包含 Cookie 等信息，但不包含 _get_request 的 UA 轮询逻辑)
                # 可以在这里显式设置一下当前 session header
                # ImageDownloader 最好也由外部传入带 headers 的 session
                downloaded_files, download_success = self.image_downloader.download_images(
                    image_links, url, os.path.join(output_path, "images")
                )
                if download_success:
                    logger.info(f"图片下载成功，共下载 {len(downloaded_files)} 张")
                else:
                    logger.error("部分图片下载失败")
                    # 这里是否抛异常取决于策略，如果图片失败不影响元数据保存，则不抛出
                    # raise Exception("图片下载失败")

            existing_avatar = existing_data.get('avatar', '') if isinstance(existing_data, dict) else ''
            brand = os.path.basename(base_dir) if base_dir else ""
            
            product_details = ProductDetails(
                name=product_name,
                image_links=image_links,
                product_info=product_info,
                article_content=article_content,
                url=url,
                product_id=product_id,
                product_tag=product_tag,
                series=series,
                avatar=existing_avatar,
                brand=brand
            )
            
            self._save_product_details(product_details, output_path)
            
            # --- 随机延时 ---
            sleep_time = random.uniform(1.5, 3.5)
            logger.info(f"详情页抓取完成，随机延时 {sleep_time:.2f} 秒...")
            time.sleep(sleep_time)

            return product_details, output_path
            
        except Exception as e:
            logger.error(f"处理产品详情时出错: {e}", exc_info=True)
            return None

    def _scrape_p_bandai_details(self, url: str, base_dir: str, product_name: Optional[str]) -> Optional[Tuple[ProductDetails, str]]:
        """处理 Premium Bandai 商品页"""
        try:
            logger.info(f"正在访问Premium Bandai产品详情页: {url}")
            logger.info("爬不了一点，过 (PB页面策略)")
            
            # 模拟处理（实际上PB页面需要登录或特殊处理，此处仅创建文件夹占位）
            
            product_tag = "premium"
            series = "gunpla"
            product_id = self.data_extractor.extract_product_id(url)

            safe_folder_name = self.data_extractor.sanitize_folder_name(product_name or "premium_item")
            
            if product_id:
                folder_name = f"{product_id}_{safe_folder_name}"
            else:
                folder_name = safe_folder_name
                
            output_path = os.path.join(base_dir, folder_name)
            
            if not os.path.exists(output_path):
                old_path = os.path.join(base_dir, safe_folder_name)
                if os.path.exists(old_path) and product_id:
                     logger.info(f"迁移文件夹: {old_path} -> {output_path}")
                     try:
                         os.rename(old_path, output_path)
                     except Exception as e:
                         logger.error(f"迁移文件夹失败: {e}")

            image_links: List[str] = []
            
            # 读取旧数据
            existing_avatar = ''
            existing_name = product_name
            existing_info = ""
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
                    pass

            brand = os.path.basename(base_dir) if base_dir else ""
            details = ProductDetails(
                name=existing_name,
                image_links=image_links,
                product_info=existing_info,
                article_content="",
                url=url,
                product_id=product_id,
                product_tag=product_tag,
                series=series,
                avatar=existing_avatar,
                brand=brand
            )

            self._save_product_details(details, output_path)
            
            # 即使是PB页面，如果是真实请求了也应该延时，这里虽未请求但保持一致性
            time.sleep(random.uniform(0.5, 1.5))
            
            return details, output_path

        except Exception as e:
            logger.error(f"处理Premium Bandai详情时出错: {e}")
            return None
    
    def _save_product_list(self, results: List[ProductLink]):
        """保存产品列表到文件"""
        data = []
        for result in results:
            data.append({
                'href': result.href,
                'text': result.text,
            })
        
        with open(SCRAPED_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"产品列表已保存到: {SCRAPED_DATA_FILE}")
    
    def _smart_merge(self, old_data: dict, new_data: dict) -> dict:
        """
        智能合并数据
        规则：
        1. key 不在 old_data -> 写入
        2. key 在 old_data:
            - new_value 非空 -> 覆盖
            - new_value 为空 -> 保留 old_value
        3. 如果值都是字典，递归合并
        """
        merged = old_data.copy()
        
        for key, new_value in new_data.items():
            if key not in merged:
                merged[key] = new_value
            else:
                old_value = merged[key]
                
                # 递归合并字典
                if isinstance(old_value, dict) and isinstance(new_value, dict):
                    merged[key] = self._smart_merge(old_value, new_value)
                    continue

                # 判断是否为空 (None, "", [], {})
                # 注意：0 应该被视为非空，但 False 呢？通常爬虫数据很少有 False，主要是 None, "", []
                # 这里严格按照 "非 None, 非空字符串, 非空列表"
                is_empty = new_value is None
                if isinstance(new_value, (str, list, dict)):
                    if len(new_value) == 0:
                        is_empty = True
                
                if not is_empty:
                    merged[key] = new_value
                # else: keep old value
                
        return merged

    def _save_product_details(self, product_details: ProductDetails, output_path: str = None):
        """保存产品详情到文件"""
        file_path = "product_details.json"
        if output_path:
            os.makedirs(output_path, exist_ok=True)
            file_path = os.path.join(output_path, "product_details.json")
            
        old_data = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
            except Exception as e:
                logger.warning(f"读取旧数据失败: {e}，将使用新数据覆盖")
                old_data = {}
        
        new_data = product_details.to_dict()
        final_data = self._smart_merge(old_data, new_data)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logger.info(f"产品详情已保存到: {file_path}")

    def test_scrape_product_list(self):
        """测试产品列表爬取功能"""
        print("\n" + "="*60)
        logger.info("测试: 产品列表爬取")
        print("="*60)
        
        # 默认测试第一页
        result = self.scrape_product_list(num_pages=1, base_url=PRODUCT_LIST_URL)
        
        if result.success:
            logger.info("测试通过！")
            logger.info(f"成功获取 {len(result.data)} 个产品链接")
            for i, link in enumerate(result.data[:3], 1):
                print(f"   {i}. {link.text}")
        else:
            logger.error("测试失败！")
            logger.error(f"错误: {result.error_message}")
        
        return result

if __name__ == "__main__":
    # 直接运行测试
    scraper = BandaiScraper()
    scraper.test_scrape_product_list()