"""
디시인사이드 공포 갤러리 크롤러
https://gall.dcinside.com/mgallery/board/lists/?id=gongpow

출력: database/data/dcinside_horror.json
"""
import json, re, time, os, sys
import urllib.request
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT = os.path.join(BASE_DIR, 'database', 'data', 'dcinside_horror.json')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://gall.dcinside.com',
}

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if i < retries - 1:
                time.sleep(2)
            else:
                print(f'  요청 실패: {e}')
    return ''

def clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_post_list(page):
    url = f'https://gall.dcinside.com/mgallery/board/lists/?id=gongpow&page={page}'
    html = fetch(url)
    # 게시글 view 링크에서 번호 추출
    links = re.findall(r'/mgallery/board/view/\?id=gongpow&no=(\d+)', html)
    return list(dict.fromkeys(links))

def get_post(no):
    url = f'https://gall.dcinside.com/mgallery/board/view/?id=gongpow&no={no}'
    html = fetch(url)
    if not html:
        return None

    # 제목
    title_match = re.search(r'<h3 class="title[^"]*"[^>]*>\s*<span[^>]*>(.*?)</span>', html, re.S)
    if not title_match:
        title_match = re.search(r'og:title" content="([^"]+)"', html)
    title = clean_html(title_match.group(1)) if title_match else ''

    if not title or len(title) < 5:
        return None

    # 본문 - 중첩 div 처리
    body = ''
    idx = html.find('<div class="write_div"')
    if idx >= 0:
        chunk = html[idx:]
        content_start = chunk.find('>') + 1
        depth, i = 0, content_start
        while i < len(chunk):
            if chunk[i:i+4] == '<div':
                depth += 1
                i += 4
            elif chunk[i:i+6] == '</div>':
                if depth == 0:
                    break
                depth -= 1
                i += 6
            else:
                i += 1
        body = clean_html(chunk[content_start:i])

    if len(body) < 100:
        return None

    # JS 코드/광고 필터
    if any(kw in body for kw in ['dc official App', 'window.OutLink', 'function()', 'javascript:']):
        return None
    if any(kw in body[:200] for kw in ['클릭', '바로가기', '광고', '이벤트']):
        return None
    # 성인 내용 필터
    if any(kw in body for kw in ['딸딸이', '자위', '포르노', '야동']):
        return None

    return {
        'title': title[:200],
        'content': body[:3000],
        'region': '한국',
        'source': 'dcinside_gongpow',
    }

def run():
    print(f'디시인사이드 공포 갤러리 크롤링 시작 (끝까지)', flush=True)
    results = []
    seen_nos = set()
    page = 1

    while True:
        print(f'  페이지 {page} 처리 중...', flush=True)
        nos = get_post_list(page)
        new_nos = [n for n in nos if n not in seen_nos]

        if not nos:
            print('더 이상 페이지 없음. 완료.')
            break

        seen_nos.update(nos)

        for no in new_nos:
            post = get_post(no)
            if post:
                results.append(post)
            time.sleep(0.5)

        print(f'    수집: {len(results)}건', flush=True)
        time.sleep(1)
        page += 1

    # 기존 파일과 병합
    existing = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding='utf-8') as f:
            existing = json.load(f)
        existing_titles = {s['title'] for s in existing}
        results = [r for r in results if r['title'] not in existing_titles]
        print(f'기존 {len(existing)}건 + 신규 {len(results)}건')
        results = existing + results

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'저장 완료: {OUTPUT} ({len(results)}건)')

if __name__ == '__main__':
    run()
