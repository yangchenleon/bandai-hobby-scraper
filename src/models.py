#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型类
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class ProductLink:
    """产品链接信息"""
    href: Optional[str]
    text: str
    avatar: Optional[str] = None
    
    def __str__(self):
        return f"ProductLink(text='{self.text}', href='{self.href}')"


@dataclass
class ProductDetails:
    """产品详细信息"""
    name: str
    image_links: List[str]
    product_info: Dict[str, str]
    article_content: str
    url: str
    product_tag: str = ""  # 产品标签
    series: str = ""  # 系列链接
    avatar: str = ""  # 列表卡片头像图链接
    brand: str = ""  # 品牌标识
    
    def __str__(self):
        return f"ProductDetails(name='{self.name}', images={len(self.image_links)}, info_items={len(self.product_info)})"
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'product_name': self.name,
            'image_links': self.image_links,
            'product_info': self.product_info,
            'article_content': self.article_content,
            'url': self.url,
            'product_tag': self.product_tag,
            'series': self.series,
            'avatar': self.avatar,
            'brand': self.brand
        }


@dataclass
class ScrapingResult:
    """爬取结果"""
    success: bool
    data: Optional[List[ProductLink]] = None
    error_message: Optional[str] = None
    
    def __str__(self):
        if self.success:
            return f"ScrapingResult(success=True, items={len(self.data) if self.data else 0})"
        else:
            return f"ScrapingResult(success=False, error='{self.error_message}')"
