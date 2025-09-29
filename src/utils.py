#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import os
import time
import re
import requests
from urllib.parse import urlparse
from typing import Optional


def clean_text(text: str) -> str:
    """
    清理文本内容
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 去除多余的空格，将多个连续空格替换为单个空格
    text = ' '.join(text.split())
    
    # 特殊处理价格格式
    if '円' in text:
        # 对于价格，保持数字和货币符号之间的适当间距
        text = re.sub(r'(\d+)\s*円', r'\1円', text)
        text = re.sub(r'(\d+)\s*\(', r'\1(', text)
    
    return text


def normalize_url(url: str, base_url: str = "https://bandai-hobby.net") -> str:
    """
    标准化URL
    
    Args:
        url: 原始URL
        base_url: 基础URL
        
    Returns:
        标准化后的URL
    """
    if not url:
        return ""
    
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return base_url + url
    
    return url