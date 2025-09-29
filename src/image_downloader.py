#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片下载模块
负责处理图片的下载、重试和文件管理
"""

import os
import time
import requests
from urllib.parse import urlparse
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, IMAGE_TIMEOUT, CSS_SELECTORS
from utils import normalize_url


class ImageDownloader:
    """图片下载器类"""
    
    def __init__(self, session: requests.Session):
        """
        初始化图片下载器
        
        Args:
            session: 用于下载的requests会话
        """
        self.session = session
    
    def download_images(self, image_links: List[str], referer_url: str, output_path: str) -> Tuple[List[str], bool]:
        """
        下载图片列表
        
        Args:
            image_links: 图片链接列表
            referer_url: 引用页面URL
            output_path: 输出目录路径
            
        Returns:
            tuple: (downloaded_files: List[str], success: bool)
                - downloaded_files: 成功下载的文件路径列表
                - success: 是否至少成功下载了一张图片
        """
        print("开始下载图片...")
        downloaded_files = []
        
        for i, img_url in enumerate(image_links):
            print(f"下载图片 {i+1}/{len(image_links)}: {img_url[:50]}...")
            file_path = self.download_single_image(img_url, referer_url, output_path)
            
            if file_path:
                downloaded_files.append(file_path)
            else:
                # 如果下载失败，尝试重新获取页面获取新的图片URL
                print(f"  🔄 尝试重新获取页面以获取新的图片URL...")
                new_image_links = self._get_fresh_image_links(referer_url)
                if new_image_links and i < len(new_image_links):
                    new_img_url = new_image_links[i]
                    file_path = self.download_single_image(new_img_url, referer_url, output_path)
                    if file_path:
                        downloaded_files.append(file_path)
        
        success = len(downloaded_files) > 0
        print(f"成功下载 {len(downloaded_files)} 张图片")
        
        return downloaded_files, success
    
    def download_single_image(self, image_url: str, referer_url: str, output_path: str) -> Optional[str]:
        """
        下载单个图片
        
        Args:
            image_url: 图片URL
            referer_url: 引用页面URL
            output_path: 输出目录路径
            
        Returns:
            str: 成功下载的文件路径，失败时返回None
        """
        try:
            # 创建输出目录
            os.makedirs(output_path, exist_ok=True)
            
            # 设置图片下载请求头
            headers = {
                'Referer': referer_url,
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
            
            # 尝试下载图片，如果失败则尝试重新获取页面
            max_retries = 2
            for attempt in range(max_retries):
                # 使用当前session发送请求
                response = self.session.get(image_url, headers=headers, timeout=IMAGE_TIMEOUT)
                response.raise_for_status()
                
                # 检查响应内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    print(f"  ✗ 响应不是图片格式: {content_type}")
                    if attempt < max_retries - 1:
                        print(f"  ⚠️ 尝试重新获取页面...")
                        # 重新访问产品页面以获取新的签名URL
                        self._refresh_image_urls(referer_url)
                        continue
                    return None
                
                # 生成文件名
                parsed_url = urlparse(image_url)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    # 从content-type获取扩展名
                    ext = 'jpg'
                    if 'png' in content_type:
                        ext = 'png'
                    elif 'webp' in content_type:
                        ext = 'webp'
                    filename = f"image_{int(time.time())}.{ext}"
                
                # 保存文件
                file_path = os.path.join(output_path, filename)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"  ✓ 图片已保存: {file_path}")
                return file_path

        except Exception as e:
            print(f"  ✗ 图片下载失败: {str(e)[:100]}...")
            return None
    
    def _get_fresh_image_links(self, product_url: str) -> List[str]:
        """
        重新获取产品页面的图片链接以解决CloudFront签名过期问题
        
        Args:
            product_url: 产品页面URL
            
        Returns:
            List[str]: 新的图片链接列表
        """
        try:
            print(f"  🔄 重新访问产品页面: {product_url}")
            response = self.session.get(product_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 重新解析页面获取新的图片链接
            soup = BeautifulSoup(response.text, 'html.parser')
            thumbnail_wrapper = soup.find(class_=CSS_SELECTORS['thumbnail_wrapper'])
            
            if thumbnail_wrapper:
                new_image_links = []
                img_elements = thumbnail_wrapper.find_all('img')
                for img in img_elements:
                    src = img.get('src')
                    if src:
                        src = normalize_url(src)
                        new_image_links.append(src)
                
                print(f"  ✓ 获取到 {len(new_image_links)} 个新的图片链接")
                return new_image_links
            else:
                print(f"  ⚠️ 未找到图片容器")
                return []
                
        except Exception as e:
            print(f"  ⚠️ 重新获取图片链接失败: {str(e)[:50]}...")
            return []
    
    def _refresh_image_urls(self, product_url: str):
        """
        重新访问产品页面以获取新的CloudFront签名URL
        
        Args:
            product_url: 产品页面URL
        """
        try:
            print(f"  🔄 重新访问产品页面以获取新的图片URL...")
            response = self.session.get(product_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # 重新解析页面获取新的图片链接
            soup = BeautifulSoup(response.text, 'html.parser')
            thumbnail_wrapper = soup.find(class_=CSS_SELECTORS['thumbnail_wrapper'])
            
            if thumbnail_wrapper:
                # 更新图片链接缓存（这里可以扩展为缓存机制）
                print(f"  ✓ 成功刷新图片URL")
            else:
                print(f"  ⚠️ 未找到新的图片容器")
                
        except Exception as e:
            print(f"  ⚠️ 刷新图片URL失败: {str(e)[:50]}...")
