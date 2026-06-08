"""
SCP 재단 한국어 위키 크롤러
https://ko.scp-wiki.net

출력: processing/preprocessed_scp.json
형식: {code, title, korean_name, text, object_class, tags, source_url}
"""
import json, re, time, os, sys
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8')

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, 'processing')
OUTPUT = os.path.join(OUTPUT_DIR, 'preprocessed_scp.json')
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_URL = 'https://ko.scp-wiki.net'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# 실제 SCP 항목이 아닌 페이지 필터 키워드
SKIP_BODY_KEYWORDS = ['목록 KO', '목록 EN', '시리즈 목록', 'SCP 인터내셔널', '이거 무슨 페이지']


def fetch(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if i < 2:
                time.sleep(0.5)
            else:
                print(f'  실패: {url} - {e}')
    return ''


def clean(text):
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.S)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-z#\d]+;', ' ', text)
    text = re.sub(r'\s{3,}', '\n\n', text)
    return text.strip()


def get_links_from_series(path):
    """시리즈 목록에서 개별 SCP 링크 추출"""
    html = fetch(BASE_URL + path)
    if not html:
        return []
    links = re.findall(r'href="(/scp-[\d]+[a-z-]*)"', html)
    skip = {'series', 'hub', 'tales', 'edition', 'list', 'ex', 'glossary', 'artwork'}
    result = []
    seen = set()
    for link in links:
        if link in seen:
            continue
        if any(s in link for s in skip):
            continue
        seen.add(link)
        result.append(link)
    return result


def parse_scp(path):
    """개별 SCP 페이지 파싱"""
    url = BASE_URL + path
    html = fetch(url)
    if not html:
        return None

    # SCP 번호 추출
    code_m = re.search(r'scp-([\d]+[\w-]*)', path, re.I)
    code = f'SCP-{code_m.group(1).upper()}' if code_m else path.strip('/').upper()

    # 제목: page-title div에서 직접 추출 (span 없음)
    title = code
    pt = re.search(r'id="page-title"[^>]*>\s*([^\n<]{2,80})', html)
    if pt:
        candidate = pt.group(1).strip()
        if candidate:
            title = candidate

    # 본문 추출
    m = re.search(r'id="page-content"[^>]*>(.*)', html, re.S)
    if not m:
        return None
    raw_body = m.group(1)

    # 평가/푸터 섹션 이전까지만
    cut = re.search(r'id="(page-rating|footer-wikiwalk|rate-box|page-tags)"', raw_body)
    if cut:
        raw_body = raw_body[:cut.start()]

    # info-container (저작권/작가 정보 블록) 제거
    raw_body = re.sub(r'<div[^>]*class="[^"]*info-container[^"]*"[^>]*>.*?</div>\s*</div>\s*</div>', '', raw_body, flags=re.S)

    body = clean(raw_body)

    if len(body) < 200:
        return None

    # 내비게이션/목록 페이지 필터
    if any(kw in body[:500] for kw in SKIP_BODY_KEYWORDS):
        return None

    # 한국어 SCP 이름 추출: "SCP-xxx: 이름" 패턴
    korean_name = ''
    name_m = re.search(rf'{re.escape(code)}[:\s]+([^\n<]{{2,50}})', body)
    if name_m:
        candidate = name_m.group(1).strip().rstrip('.')
        if candidate and not candidate.startswith('SCP'):
            korean_name = candidate

    # 격리 등급 (한국어/영어 모두 처리)
    obj_class = 'Unknown'
    for pat in [
        r'등급\s*[:\-]\s*([^\n<]{1,30})',
        r'격리 등급\s*[:\-]\s*([^\n<]{1,30})',
        r'개체 등급\s*[:\-]\s*([^\n<]{1,30})',
        r'\b(Keter|Euclid|Safe|Thaumiel|Apollyon|Neutralized|Explained|케테르|유클리드|안전|타우미엘|아폴리온|중화됨|해명됨)\b',
    ]:
        c = re.search(pat, body, re.I)
        if c:
            obj_class = c.group(1).strip()
            break

    # 태그
    tags = []
    tag_div = re.search(r'<div[^>]*class="[^"]*page-tags[^"]*"[^>]*>(.*?)</div>', html, re.S)
    if tag_div:
        tags = [t.strip() for t in re.findall(r'<a[^>]*>([^<]+)</a>', tag_div.group(1)) if t.strip()]

    return {
        'code': code,
        'title': title,
        'korean_name': korean_name,
        'text': body[:5000],
        'object_class': obj_class,
        'tags': tags,
        'source_url': url,
    }


def run():
    print('SCP 한국어 위키 크롤링 시작')

    existing = []
    # 기존 파일이 있어도 재크롤링 (파서 수정으로 품질 개선)
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding='utf-8') as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []
    print(f'기존: {len(existing)}건')

    series_pages = [
        '/scp-series',    # 001~999
        '/scp-series-2',  # 1000~1999
        '/scp-series-3',  # 2000~2999
        '/scp-series-4',  # 3000~3999
        '/scp-series-5',  # 4000~4999
        '/scp-series-6',  # 5000~5999
        '/scp-series-7',  # 6000~6999
    ]

    all_links = []
    print('링크 수집 중...')
    for sp in series_pages:
        links = get_links_from_series(sp)
        new = [l for l in links if l not in all_links]
        all_links.extend(new)
        print(f'  {sp}: +{len(new)}개 (누적 {len(all_links)})')
        time.sleep(0.3)

    print(f'\n총 링크: {len(all_links)}개, 크롤링 시작...')

    results = []
    existing_codes = set()
    ok = fail = skip = 0

    for i, path in enumerate(all_links):
        item = parse_scp(path)
        if item and item['code'] not in existing_codes:
            results.append(item)
            existing_codes.add(item['code'])
            ok += 1
            if ok % 20 == 0:
                print(f'  [{i+1}/{len(all_links)}] {item["code"]}: {item.get("korean_name") or item["title"]} | {item["object_class"]} (ok={ok})')
        else:
            fail += 1
            if fail % 50 == 0:
                print(f'  [{i+1}/{len(all_links)}] 실패/건너뜀 누적: {fail}건')

        if (i + 1) % 100 == 0:
            with open(OUTPUT, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f'  중간 저장: {len(results)}건')

        time.sleep(0.3)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'\n완료: {len(results)}건 (성공 {ok}, 실패 {fail})')
    print(f'저장: {OUTPUT}')


if __name__ == '__main__':
    run()
