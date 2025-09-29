#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据提取模块
负责从HTML页面中提取各种产品信息
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple

from config import CSS_SELECTORS
from utils import clean_text, normalize_url


class DataExtractor:
    """数据提取器类"""
    
    def __init__(self):
        """初始化数据提取器"""
        pass
    
    def extract_product_name(self, soup: BeautifulSoup) -> str:
        """
        提取产品名称
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            str: 产品名称
        """
        product_name_element = soup.find(class_=CSS_SELECTORS['product_name'])
        return product_name_element.get_text(strip=True) if product_name_element else ""
    
    def extract_image_links(self, soup: BeautifulSoup) -> List[str]:
        """
        提取图片链接列表
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            List[str]: 图片链接列表
        """
        thumbnail_wrapper = soup.find(class_=CSS_SELECTORS['thumbnail_wrapper'])
        image_links = []
        
        if thumbnail_wrapper:
            img_elements = thumbnail_wrapper.find_all('img')
            for img in img_elements:
                src = img.get('src')
                if src:
                    src = normalize_url(src)
                    image_links.append(src)
            
            print(f"找到 {len(image_links)} 个缩略图")
        else:
            print("未找到缩略图容器")
        
        return image_links
    
    def extract_product_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        提取产品详细信息
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            Dict[str, str]: 产品信息字典
        """
        details_section = soup.find(class_=CSS_SELECTORS['product_details'])
        product_info = {}
        
        if details_section:
            dt_elements = details_section.find_all('dt', class_=CSS_SELECTORS['detail_label'])
            print(f"找到 {len(dt_elements)} 个标签")
            
            for dt in dt_elements:
                # 获取key (标签名)
                label_inner = dt.find(class_=CSS_SELECTORS['detail_label_inner'])
                key = label_inner.get_text(strip=True) if label_inner else ""
                
                # 查找对应的dd元素（包含标签值）
                dd = dt.find_next_sibling('dd', class_=CSS_SELECTORS['detail_label_text'])
                value = dd.get_text(strip=True) if dd else ""
                
                # 清理文本
                value = clean_text(value)
                
                if key and value:
                    product_info[key] = value
                    print(f"  {key}: {value}")
        else:
            print("未找到产品详细信息区域")
        
        return product_info
    
    def extract_article_content(self, soup: BeautifulSoup) -> str:
        """
        提取产品文章内容
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            str: 文章内容
        """
        article_section = soup.find(class_=CSS_SELECTORS['product_article'])
        
        if article_section:
            # 处理HTML内容
            html_content = str(article_section)
            html_content = html_content.replace('<br/>', ' ')
            
            # 重新解析处理后的HTML
            temp_soup = BeautifulSoup(html_content, 'html.parser')
            article_content = temp_soup.get_text(separator='\n', strip=False)
            
            return article_content
        else:
            print("未找到产品文章区域")
            return ""
    
    def extract_product_tag(self, soup: BeautifulSoup) -> str:
        """
        提取产品标签信息
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            str: 产品标签，如"online"、"gbase"等，未找到时返回空字符串
        """
        # 查找class包含pg-products__tag的元素
        tag_elements = soup.find_all(class_=lambda x: x and 'pg-products__tag' in x)
        
        for element in tag_elements:
            class_list = element.get('class', [])
            for class_name in class_list:
                # 查找以-开头的class（如-gbase）
                if class_name.startswith('-'):
                    tag = class_name[1:].strip()  # 去掉开头的-号
                    print(f"找到产品标签: {tag}")
                    return tag
        
        print("未找到产品标签")
        return ""
    
    def extract_series_links(self, soup: BeautifulSoup) -> str:
        """
        提取系列链接信息
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            str: 系列链接列表，用分号分割，如"g-reco;unicorn;seed"
        """
        # 查找class为c-card__flat p-card__flat的元素
        series_elements = soup.find_all('a', class_='c-card__flat p-card__flat')
        
        series_list = []
        for element in series_elements:
            href = element.get('href', '')
            if href:
                # 从URL中提取系列名称，如从/series/g-reco/提取g-reco
                if '/series/' in href:
                    # 提取/series/后面的部分，去掉末尾的/
                    series_name = href.split('/series/')[-1].rstrip('/')
                    if series_name:
                        series_list.append(series_name)
                        print(f"找到系列链接: {series_name}")
        
        if series_list:
            result = ';'.join(series_list)
            print(f"提取到系列链接: {result}")
            return result
        else:
            print("未找到系列链接")
            return ""
    
    def sanitize_folder_name(self, folder_name: str) -> str:
        """
        清理文件夹名称，移除非法字符
        
        Args:
            folder_name: 原始文件夹名称
            
        Returns:
            str: 清理后的文件夹名称
        """
        # 移除或替换非法字符
        folder_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
        # 移除多余的空格和点
        folder_name = re.sub(r'\s+', ' ', folder_name).strip()
        folder_name = folder_name.strip('.')
        # 限制长度
        if len(folder_name) > 100:
            folder_name = folder_name[:100]
        return folder_name
