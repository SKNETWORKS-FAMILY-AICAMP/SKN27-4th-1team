"""
동아시아 공포/괴담/민간전승 크롤러
Wikipedia API + deep-translator (무료)

출력: database/data/eastasia_horror.json
대상: 중국, 태국, 필리핀, 인도, 티베트/네팔
"""
import json, time, os, sys, re
import urllib.request, urllib.parse
from deep_translator import GoogleTranslator

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT = os.path.join(BASE_DIR, 'database', 'data', 'eastasia_horror.json')

# 나라별 Wikipedia 카테고리 + 언어 설정
TARGETS = {
    '중국': {
        'lang': 'zh',
        'categories': [
            '中国民间传说', '中国鬼怪', '中国神话', '中国妖怪',
            '中国都市传说', '中国灵异故事',
        ],
        'src_lang': 'zh-CN',
        'region': '중국',
    },
    '태국': {
        'lang': 'th',
        'categories': [
            'ผีในวัฒนธรรมไทย', 'ตำนานไทย', 'ความเชื่อพื้นบ้านไทย',
        ],
        'src_lang': 'th',
        'region': '태국',
        # 태국어 카테고리가 빈약하면 영어 보완
        'fallback_lang': 'en',
        'fallback_categories': [
            'Thai_folklore', 'Thai_mythology', 'Thai_ghosts',
        ],
    },
    '필리핀': {
        'lang': 'en',
        'categories': [
            'Philippine_mythology', 'Philippine_folklore',
            'Filipino_mythology', 'Supernatural_beings_in_Filipino_folklore',
        ],
        'src_lang': 'en',
        'region': '필리핀',
    },
    '인도': {
        'lang': 'en',
        'categories': [
            'Indian_folklore', 'Hindu_legendary_creatures',
            'Ghosts_in_Hindu_mythology', 'Indian_ghost_legends',
        ],
        'src_lang': 'en',
        'region': '인도',
    },
    '티베트/네팔': {
        'lang': 'en',
        'categories': [
            'Tibetan_mythology', 'Tibetan_folklore',
            'Nepalese_folklore', 'Tibetan_Buddhist_mythology',
        ],
        'src_lang': 'en',
        'region': '티베트/네팔',
    },
}

translator_cache = {}

def translate_to_korean(text: str, src: str) -> str:
    if not text or src == 'ko':
        return text
    key = (src, text[:50])
    if key in translator_cache:
        return translator_cache[key]
    try:
        result = GoogleTranslator(source=src, target='ko').translate(text[:4000])
        translator_cache[key] = result
        time.sleep(0.3)
        return result
    except Exception as e:
        print(f'    번역 실패: {e}')
        return text


def wiki_api(lang: str, action: str, **params) -> dict:
    base = f'https://{lang}.wikipedia.org/w/api.php'
    params.update({'action': action, 'format': 'json'})
    url = base + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 HorrorCrawler/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f'    API 오류 ({lang}): {e}')
        return {}


def get_category_members(lang: str, category: str, limit: int = 30) -> list:
    data = wiki_api(lang, 'query',
        list='categorymembers',
        cmtitle=f'Category:{category}',
        cmlimit=limit,
        cmtype='page',
    )
    pages = data.get('query', {}).get('categorymembers', [])
    return [p['title'] for p in pages if p.get('ns', 0) == 0]


def get_page_extract(lang: str, title: str) -> str:
    data = wiki_api(lang, 'query',
        titles=title,
        prop='extracts',
        exintro=True,
        explaintext=True,
        exsectionformat='plain',
    )
    pages = data.get('query', {}).get('pages', {})
    for page in pages.values():
        text = page.get('extract', '')
        if text:
            # 위키 불필요 패턴 제거
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'==+[^=]+=+', '', text)
            text = text.strip()
            return text
    return ''


def crawl_country(name: str, config: dict) -> list:
    results = []
    seen_titles = set()
    lang = config['lang']
    src_lang = config['src_lang']
    region = config['region']

    # 카테고리 목록 수집
    categories = config.get('categories', [])
    fallback_lang = config.get('fallback_lang')
    fallback_cats = config.get('fallback_categories', [])

    all_titles = []
    for cat in categories:
        titles = get_category_members(lang, cat, limit=20)
        all_titles.extend([(lang, src_lang, t) for t in titles])
        time.sleep(0.5)

    # fallback 카테고리
    if fallback_lang and fallback_cats:
        for cat in fallback_cats:
            titles = get_category_members(fallback_lang, cat, limit=20)
            all_titles.extend([(fallback_lang, 'en', t) for t in titles])
            time.sleep(0.5)

    print(f'  [{name}] 수집된 제목: {len(all_titles)}개')

    for page_lang, page_src, title in all_titles:
        if title in seen_titles:
            continue
        seen_titles.add(title)

        extract = get_page_extract(page_lang, title)
        if not extract or len(extract) < 100:
            continue

        # 한국어 번역
        ko_title = translate_to_korean(title, page_src)
        ko_content = translate_to_korean(extract[:3000], page_src)

        if not ko_title or not ko_content or len(ko_content) < 80:
            continue

        results.append({
            'title': ko_title,
            'content': ko_content,
            'region': region,
            'source': f'wikipedia_{page_lang}',
        })
        print(f'    ✓ {ko_title[:40]}')
        time.sleep(0.5)

    print(f'  [{name}] 완료: {len(results)}건')
    return results


def run():
    all_results = []

    for name, config in TARGETS.items():
        print(f'\n=== {name} 크롤링 시작 ===')
        try:
            results = crawl_country(name, config)
            all_results.extend(results)
        except Exception as e:
            print(f'  {name} 오류: {e}')

    # 기존 파일과 병합
    existing = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding='utf-8') as f:
            existing = json.load(f)
        existing_titles = {s['title'] for s in existing}
        all_results = [r for r in all_results if r['title'] not in existing_titles]
        print(f'\n기존 {len(existing)}건 + 신규 {len(all_results)}건')
        all_results = existing + all_results

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f'\n저장 완료: {OUTPUT} ({len(all_results)}건)')


if __name__ == '__main__':
    run()
