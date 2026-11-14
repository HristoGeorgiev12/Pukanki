import json
import os
import requests
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

f2k = json.load(open(os.path.join(DATA_DIR, 'filmi2k_bg.json'), encoding='utf-8'))
fen = json.load(open(os.path.join(DATA_DIR, 'filmifen_bg.json'), encoding='utf-8'))
m = json.load(open(os.path.join(DATA_DIR, 'movies.json'), encoding='utf-8'))

samples = defaultdict(list)
for d in [f2k, fen, m[:20]]:
    for item in d:
        for s in item.get('player_sources', []):
            name = s.get('name')
            url = s.get('embed_url')
            if name and url and len(samples[name]) < 3:
                samples[name].append(url)

print(f"{'Provider':24} | {'Status':16} | {'X-Frame':12} | {'CSP Restriction':16}")
print("-" * 75)

for name in sorted(samples.keys()):
    urls = samples[name]
    status_list = []
    xframe_list = set()
    csp_list = set()
    for u in urls:
        try:
            res = requests.get(
                u,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                    'Referer': 'http://localhost:8080/'
                },
                timeout=7
            )
            status_list.append(str(res.status_code))
            xf = res.headers.get('X-Frame-Options')
            if xf:
                xframe_list.add(xf)
            csp = res.headers.get('Content-Security-Policy', '')
            if 'frame-ancestors' in csp:
                csp_list.add('frame-ancestors')
        except Exception as e:
            status_list.append(type(e).__name__)

    st_str = ", ".join(status_list)
    xf_str = ", ".join(xframe_list) if xframe_list else "None"
    csp_str = ", ".join(csp_list) if csp_list else "None"
    print(f"{name:24} | {st_str:16} | {xf_str:12} | {csp_str:16}")

