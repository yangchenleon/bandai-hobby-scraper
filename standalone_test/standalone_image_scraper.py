#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的万代产品图片爬虫
专门用于访问 https://bandai-hobby.net/item/01_6782/ 产品页面的图片
解决CloudFront访问被拒绝的问题
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from urllib.parse import urlparse, urljoin
from typing import List, Optional


class BandaiImageScraper:
    """万代产品图片爬虫类"""
    
    def __init__(self):
        self.session = requests.Session()
        # 设置更真实的浏览器请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
    
    def scrape_product_images(self, product_url: str) -> List[str]:
        """
        抓取产品页面的图片链接
        
        Args:
            product_url: 产品页面URL
            
        Returns:
            List[str]: 图片链接列表
        """
        try:
            print(f"正在访问产品页面: {product_url}")
            response = self.session.get(product_url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容长度: {len(response.text)} 字符")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找缩略图容器
            thumbnail_wrapper = soup.find(class_='swiper-wrapper pg-products__sliderThumbnailInner')
            image_links = []
            
            if thumbnail_wrapper:
                img_elements = thumbnail_wrapper.find_all('img')
                for img in img_elements:
                    src = img.get('src')
                    if src:
                        # 标准化URL
                        src = self._normalize_url(src, product_url)
                        image_links.append(src)
                
                print(f"找到 {len(image_links)} 个缩略图")
                
                # 下载所有图片
                if image_links:
                    self._download_images(image_links, product_url)
                
                return image_links
            else:
                print("未找到缩略图容器，尝试查找其他图片...")
                # 查找页面中的所有图片
                all_images = soup.find_all('img')
                for img in all_images:
                    src = img.get('src')
                    if src and 'cloudfront.net' in src:
                        src = self._normalize_url(src, product_url)
                        image_links.append(src)
                
                print(f"找到 {len(image_links)} 个图片")
                if image_links:
                    self._download_images(image_links, product_url)
                
                return image_links
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return []
        except Exception as e:
            print(f"解析错误: {e}")
            return []
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """标准化URL"""
        if not url:
            return ""
        
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urljoin(base_url, url)
        
        return url
    
    def _download_images(self, image_links: List[str], referer_url: str):
        """下载图片"""
        print("开始下载图片...")
        downloaded_files = []
        
        # 创建输出目录
        output_dir = "product_images"
        os.makedirs(output_dir, exist_ok=True)
        
        for i, img_url in enumerate(image_links):
            print(f"下载图片 {i+1}/{len(image_links)}: {img_url[:50]}...")
            file_path = self._download_single_image(img_url, referer_url, output_dir)
            if file_path:
                downloaded_files.append(file_path)
        
        print(f"成功下载 {len(downloaded_files)} 张图片")
        
        # 保存图片链接到JSON文件
        self._save_image_links(image_links, downloaded_files)
    
    def _download_single_image(self, image_url: str, referer_url: str, output_dir: str) -> Optional[str]:
        """下载单个图片"""
        try:
            # 设置图片下载专用的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': referer_url,  # 关键：设置正确的Referer
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
            
            # 使用当前session发送请求，保持cookies
            response = self.session.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                print(f"  ✗ 响应不是图片格式: {content_type}")
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
                elif 'avif' in content_type:
                    ext = 'avif'
                filename = f"image_{int(time.time())}_{i}.{ext}"
            
            # 保存文件
            file_path = os.path.join(output_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"  ✓ 图片已保存: {file_path}")
            return file_path
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"  ✗ 图片访问被拒绝 (403): CloudFront签名问题")
            elif e.response.status_code == 404:
                print(f"  ✗ 图片不存在 (404)")
            else:
                print(f"  ✗ HTTP错误 {e.response.status_code}")
            return None
        except Exception as e:
            print(f"  ✗ 图片下载失败: {str(e)[:100]}...")
            return None
    
    def _save_image_links(self, image_links: List[str], downloaded_files: List[str]):
        """保存图片链接到JSON文件"""
        data = {
            # 'product_url': 'https://bandai-hobby.net/item/01_6721/',
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_images': len(image_links),
            'downloaded_images': len(downloaded_files),
            'image_links': image_links,
            'downloaded_files': downloaded_files
        }
        
        with open('image_links.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"图片链接已保存到: image_links.json")


def main():
    """主函数"""
    # 目标产品URL
    product_url = "https://bandai-hobby.net/item/01_6722/"
    
    print("=" * 60)
    print("万代产品图片爬虫")
    print("=" * 60)
    print(f"目标产品: {product_url}")
    print()
    
    # 创建爬虫实例
    scraper = BandaiImageScraper()
    
    # 开始爬取
    image_links = scraper.scrape_product_images(product_url)
    
    print()
    print("=" * 60)
    print("爬取完成")
    print("=" * 60)
    print(f"找到图片数量: {len(image_links)}")
    
    if image_links:
        print("\n图片链接列表:")
        for i, link in enumerate(image_links, 1):
            print(f"{i:2d}. {link}")
    else:
        print("未找到任何图片链接")


if __name__ == "__main__":
    main()
