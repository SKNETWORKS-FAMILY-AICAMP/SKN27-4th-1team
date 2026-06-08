"""
나무위키 parquet에서 크리피파스타/도시전설 추출
출력: processing/preprocessed_creepypastas.json
형식: {title, body, tags, categories, source}
"""
import json, re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

try:
    import pyarrow.parquet as pq
except ImportError:
    print("pyarrow 필요: pip install pyarrow")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET = os.path.join(BASE_DIR, 'database', 'data', 'namuwiki.parquet')
OUTPUT_DIR = os.path.join(BASE_DIR, 'processing')
OUTPUT = os.path.join(OUTPUT_DIR, 'preprocessed_creepypastas.json')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 크리피파스타/도시전설 카테고리 (탐색 결과 기반 확장)
CREEPYPASTA_CATEGORIES = {
    # 크리피파스타 직접
    '크리피파스타', 'Creepypasta', '인터넷 괴담',
    '도시전설/인터넷', '인터넷 도시전설',
    # 도시전설
    '도시전설',
    # 괴담
    '괴담', '토막글/괴담',
    # 오컬트/미스터리
    '오컬트', '미스터리', '미스터리 사건',
    # 공포 소재
    '귀신을 소재로 한 작품', '도시전설을 소재로 한 작품',
    # 공포 크리에이터/콘텐츠
    '공포 크리에이터',
    # 포켓몬 괴담 등 특정 괴담
    '포켓몬스터/괴담',
}

# 제목 키워드 (카테고리 없어도 이 키워드면 수집)
CREEPYPASTA_TITLE_KEYWORDS = [
    '크리피파스타', 'creepypasta',
    'Jeff the Killer', 'Eyeless Jack', 'Ben Drowned',
    'Smile Dog', 'NoEnd House', 'Slender Man',
    '슬렌더맨',
]

# 제외 패턴 (게임/애니/노래 등 명백한 비괴담)
EXCLUDE_PATTERNS = [
    r'\(게임\)', r'\(애니메이션\)', r'\(만화\)', r'\(드라마\)',
    r'\(영화\)', r'\(캐릭터\)', r'\(웹툰\)', r'/등장인물',
    r'/시즌 \d', r'/에피소드', r'\(음악\)', r'\(노래\)', r'\(앨범\)',
    r'네트워크 내비게이터',  # 록맨 EXE 오매칭 방지
    r'사운드 볼텍스', r'beatmania', r'GITADORA', r'Arcaea',
    r'리듬 게임', r'수록곡',
]

def clean_markup(text):
    text = re.sub(r'\[br\]', '\n', text)
    text = re.sub(r'\[목차\]|\[clearfix\]|\[각주\]', '', text)
    text = re.sub(r'파일:[^\s\n\|]+', '', text)
    text = re.sub(r'\[\*([^\]]*)\]', r'\1', text)
    text = re.sub(r'~~([^~\n]*)~~', r'\1', text)
    text = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\|\|[^\n]*', '', text)
    text = re.sub(r'^\s*[\|}{]+\s*$', '', text, flags=re.M)
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'width=\d+[^\s\n]*', '', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'</?\w+[^>]*>', '', text)
    text = re.sub(r'--[^-\n]+--', '', text)
    text = re.sub(r'분류:[^\n]+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()

def extract_categories(text):
    return {c.strip() for c in re.findall(r'\[\[분류:([^\]]+)\]\]', text)}

def is_excluded(title):
    return any(re.search(p, title) for p in EXCLUDE_PATTERNS)

print(f'parquet 로딩: {PARQUET}')
table = pq.read_table(PARQUET)
titles = table['title'].to_pylist()
texts = table['text'].to_pylist()
total = len(titles)
print(f'총 {total:,}건 검색')

results = []
seen = set()

for i, (title, raw_text) in enumerate(zip(titles, texts)):
    if not title or not raw_text:
        continue
    if any(title.startswith(p) for p in ['분류:', '파일:', '틀:', '나무위키:']):
        continue
    if title in seen:
        continue
    if is_excluded(title):
        continue

    cats = extract_categories(raw_text)

    is_cp = bool(cats & CREEPYPASTA_CATEGORIES)
    is_cp = is_cp or any(kw.lower() in title.lower() for kw in CREEPYPASTA_TITLE_KEYWORDS)

    if not is_cp:
        continue

    text = clean_markup(raw_text)
    if len(text) < 200:
        continue

    seen.add(title)
    matched_cats = list(cats & CREEPYPASTA_CATEGORIES)
    results.append({
        'title': title,
        'body': text[:5000],
        'tags': matched_cats,
        'categories': list(cats),
        'source': 'namuwiki',
    })

    if (i + 1) % 500000 == 0:
        print(f'  {i+1:,}/{total:,} 처리 중... (수집: {len(results)}건)')

print(f'\n추출 완료: {len(results)}건')

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f'저장: {OUTPUT}')
