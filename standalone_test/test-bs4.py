import requests
from bs4 import BeautifulSoup

url = "https://p-bandai.jp/item/item-1000208236/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()
response.encoding = 'utf-8'

soup = BeautifulSoup(response.text, 'html.parser')

with open('p-bandai_content.txt', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print("网页内容已保存到 p-bandai_content.txt")
