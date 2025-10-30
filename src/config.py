#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from typing import Optional

"""
配置文件
"""

# 基础URL配置
Brand = [
    "hg", "rg", "mg", "mgka",
    "mgsd", "pg", "entry_grade_g", "optionpartsset", 
    "gundam_decal", "sdcs", "SDEX", "bb",
    "re100", "fullmechanics", "mgex", "expo2025-gunpla",
    "ecoplaproject_g", "actionbase", "tool"]

# 大写品牌代码到实际网页后缀的映射
BRAND_CODE_TO_SLUG = {
    "HG": "hg",
    "RG": "rg",
    "MG": "mg",
    "MGKA": "mgka",
    "MGSD": "mgsd",
    "PG": "pg",
    "EG": "entry_grade_g",
    "OPTION": "optionpartsset",
    "DECAL": "gundam_decal",
    "SDCS": "sdcs",
    "SDEX": "SDEX",
    "BB": "bb",
    "RE": "re100",
    "FM": "fullmechanics",
    "MGEX": "mgex",
    "EXPO2025": "expo2025-gunpla",
    "ECO": "ecoplaproject_g",
    "ABASE": "actionbase",
    "TOOL": "tool",
}
BASE_URL = "https://bandai-hobby.net"
PRODUCT_LIST_URL = f"{BASE_URL}/brand/" # 分页总目录，根据这个修改爬取大类
# PRODUCT_LIST_URL = f"https://bandai-hobby.net/brand/hg/"

# 请求头配置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# 文件路径配置
OUTPUT_DIR = "/mnt/d/code/bandai-hobby-scraper/data"
SCRAPED_DATA_FILE = f"{OUTPUT_DIR}/scraped_data.json"

# 请求配置
REQUEST_TIMEOUT = 10
IMAGE_TIMEOUT = 30  # 增加图像下载超时时间到30秒

# CSS选择器配置
CSS_SELECTORS = {
    'product_cards': 'p-card__wrap c-grid -cols2-1',
    'product_name': 'p-heading__h1-product',
    'thumbnail_wrapper': 'swiper-wrapper pg-products__sliderThumbnailInner',
    'product_details': 'pg-products__detail',
    'detail_label': 'pg-products__label',
    'detail_label_inner': 'pg-products__labelInner',
    'detail_label_text': 'pg-products__labelTxt',
    'product_article': 'pg-products__article',
    'pagination_links': 'c-archives__pagination-list-item-link',  # 分页链接选择器
}

class Config:
    # 数据库配置
    DATABASE_PATH = os.getenv("DATABASE_PATH", "database/bandai_hobby.db")
    
    # 数据源配置
    DATA_DIR = os.getenv("DATA_DIR", "data")