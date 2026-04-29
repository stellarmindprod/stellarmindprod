import urllib.request
from urllib.parse import urljoin
import re
import os

url = "https://nitsikkim.ac.in/"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    banner_url = None
    for src in img_urls:
        if 'logo' in src.lower() or 'banner' in src.lower() or 'header' in src.lower():
            banner_url = urljoin(url, src)
            break
            
    if banner_url:
        print(f"Found banner URL: {banner_url}")
        req = urllib.request.Request(banner_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data = urllib.request.urlopen(req).read()
        out_path = os.path.join('static', 'images', 'header_banner.png')
        with open(out_path, 'wb') as f:
            f.write(img_data)
        print(f"Saved banner to {out_path}")
except Exception as e:
    print(f"Error: {e}")
