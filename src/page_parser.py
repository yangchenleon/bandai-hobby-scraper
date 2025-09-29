#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面解析模块
负责解析HTML页面，提取产品列表和分页信息
"""

import time
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from config import PRODUCT_LIST_URL, CSS_SELECTORS, REQUEST_TIMEOUT
from models import ProductLink, ScrapingResult


class PageParser:
    """页面解析器类"""
    
    def __init__(self, session: requests.Session):
        """
        初始化页面解析器
        
        Args:
            session: 用于请求的requests会话
        """
        self.session = session
    
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
    
    def scrape_product_list(self, num_pages: int = None, start_page: int = 1) -> ScrapingResult:
        """
        抓取产品列表页面（支持多页）
        
        Args:
            num_pages: 爬取页数，默认为5页
            start_page: 起始页码，默认为1
            
        Returns:
            ScrapingResult: 爬取结果
        """
        try:
            all_results = []
            page = start_page
            max_pages = start_page + num_pages - 1

            while page <= max_pages:
                # 构建当前页URL
                if page == 1:
                    current_url = PRODUCT_LIST_URL
                else:
                    current_url = f"{PRODUCT_LIST_URL}?p={page}"
                
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
            
            return ScrapingResult(success=True, data=all_results)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {e}"
            print(error_msg)
            return ScrapingResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"解析错误: {e}"
            print(error_msg)
            return ScrapingResult(success=False, error_message=error_msg)
    
    def parse_product_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        解析单个产品页面
        
        Args:
            url: 产品页面URL
            
        Returns:
            BeautifulSoup: 解析后的页面对象，失败时返回None
        """
        try:
            print(f"正在访问产品详情页: {url}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容长度: {len(response.text)} 字符")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
            
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
        except Exception as e:
            print(f"解析错误: {e}")
            return None
