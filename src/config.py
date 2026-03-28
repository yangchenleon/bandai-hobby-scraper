#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

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
PRODUCT_LIST_URL = f"{BASE_URL}/brand/" 

# 请求头配置 (作为备用或基础Header)
DEFAULT_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# 文件路径配置
OUTPUT_DIR = "data"  # 建议使用相对路径或通过环境变量配置
SCRAPED_DATA_FILE = os.path.join(OUTPUT_DIR, "scraped_data.json")

# 日志配置
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

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
    'pagination_links': 'c-archives__pagination-list-item-link',
}

class Config:
    # 数据库配置
    DATABASE_PATH = os.getenv("DATABASE_PATH", "database/bandai_hobby.db")
    
    # 数据源配置
    DATA_DIR = os.getenv("DATA_DIR", "data")