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

from config import IMAGE_TIMEOUT


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
            
            # 设置当前下载的文件名（不含扩展名，扩展名由下载器根据内容或URL判断）
            self._current_image_name = f"{i+1:02d}"
            
            file_path = self.download_single_image(img_url, referer_url, output_path)
            
            if file_path:
                downloaded_files.append(file_path)
            else:
                print(f"  ✗ 图片下载失败，终止本次下载任务")
                # 清除自定义文件名，避免影响其他调用
                if hasattr(self, '_current_image_name'):
                    delattr(self, '_current_image_name')
                return downloaded_files, False
        
        # 清除自定义文件名
        if hasattr(self, '_current_image_name'):
            delattr(self, '_current_image_name')
            
        success = len(downloaded_files) == len(image_links)
        print(f"成功下载 {len(downloaded_files)} / {len(image_links)} 张图片")
        
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
            
            # 单次请求下载图片，失败即返回None
            response = self.session.get(image_url, headers=headers, timeout=IMAGE_TIMEOUT)
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                print(f"  ✗ 响应不是图片格式: {content_type}")
                return None
            
            # 生成文件名 (使用序号命名)
            # 假设 image_url 中可能包含文件扩展名
            parsed_url = urlparse(image_url)
            path = parsed_url.path
            
            # 获取扩展名
            ext = 'jpg'
            if '.' in path:
                ext = path.split('.')[-1].lower()
                # 处理可能带参数的情况，虽然urlparse.path通常不带query
                if len(ext) > 4: 
                    ext = 'jpg'
            
            # 如果content-type明确，优先使用content-type
            if 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            elif 'jpeg' in content_type:
                ext = 'jpg'
                
            # 使用传入的自定义文件名（如果存在）
            if hasattr(self, '_current_image_name') and self._current_image_name:
                filename = f"{self._current_image_name}.{ext}"
            else:
                # 默认使用URL的文件名
                filename = os.path.basename(path)
                if not filename or '.' not in filename:
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
    
    # 刷新/重新获取链接相关逻辑已删除，下载失败即失败