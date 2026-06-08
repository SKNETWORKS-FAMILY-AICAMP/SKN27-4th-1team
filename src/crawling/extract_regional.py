"""
나무위키 parquet에서 특정 지역 요괴/괴담 추출 (필리핀, 태국, 티베트 등)
기존 ultimate_global_mythology_1000.json에 병합 저장
"""
import json, re, os, sys
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET_PATH = os.path.join(BASE_DIR, 'database', 'data', 'namuwiki.parquet')
YOKAI_PATH = os.path.join(BASE_DIR, 'database', 'data', 'ultimate_global_mythology_1000.json')

# 지역별 키워드
REGIONAL_KEYWORDS = {
    '필리핀': [
        '아스왕', '마나나왈', '바콩글로트', '타워', '시가비나이', '만나나왈',
        '필리핀의 요괴', '필리핀 신화', '필리핀의 귀신', '필리핀 전설',
        '아라우', '카파탈', '부사우', '뉴올론', '타옹', '아뇨', '망이크',
    ],
    '태국': [
        '크라수에', '피나이', '낭탁시', '낭악', '피가수', '피포프',
        '태국의 요괴', '태국 신화', '태국의 귀신', '태국 전설',
        '크마크', '낭엘', '피', '피 모비', '크라항', '아페', '맛',
    ],
    '티베트/네팔': [
        '예티', '미고이', '티베트 신화', '네팔 신화', '티베트의 귀신',
        '롤랑', '드레모', '나가', '신포', '캉드로마',
        '라마', '나로파', '미라레파',
    ],
    '인도': [
        '베탈', '피샤차', '나가', '야크샤', '라크샤사', '아수라',
        '인도의 요괴', '인도 신화의', '힌두 신화의 괴물', '인도 전설',
        '가루다', '나가', '마카라', '키르티무카', '간다르바',
    ],
    '중국': [
        '중국의 요괴', '중국 신화의', '중국 전설의', '요재지이',
        '산해경의', '봉신연의', '서유기의 요괴', '중국의 귀신',
        '강시', '호선', '여우정', '목련귀', '백골정',
    ],
    '서양': [
        '유럽의 요괴', '서양의 요괴', '켈트 신화', '북유럽 신화의',
        '그리스 신화의 괴물', '슬라브 신화', '게르만 신화',
        '드래곤', '뱀파이어', '늑대인간', '고블린', '트롤',
        '밴시', '세이렌', '메두사', '미노타우로스', '켄타우로스',
    ],
}

EXCLUDE_PATTERNS = [
    r'^[#&@\d]', r'\(게임\)', r'\(애니메이션\)', r'\(만화\)',
    r'\(드라마\)', r'\(음악\)', r'\(캐릭터\)', r'\(소설\)',
]

def clean_markup(text):
    text = re.sub(r'\[br\]', '\n', text)
    text = re.sub(r'\[\*([^\]]*)\]', r'\1', text)
    text = re.sub(r'~~([^~\n]*)~~', r'\1', text)
    text = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'\|\|[^\n]*', '', text)
    text = re.sub(r'\[목차\]|\[clearfix\]|\[각주\]', '', text)
    text = re.sub(r'파일:[^\s\n\|]+', '', text)
    text = re.sub(r'width=\d+[^\s\n]*', '', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'</?\w+[^>]*>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()

def is_excluded(title):
    return any(re.search(p, title) for p in EXCLUDE_PATTERNS)

def run():
    print('parquet 로딩 중...')
    table = pq.read_table(PARQUET_PATH)
    titles = table['title'].to_pylist()
    texts = table['text'].to_pylist()
    total = len(titles)
    print(f'총 {total:,}건 검색 시작')

    results = {}  # region -> list

    for i, (title, raw_text) in enumerate(zip(titles, texts)):
        if not title or not raw_text:
            continue
        if is_excluded(title):
            continue
        if any(title.startswith(p) for p in ['분류:', '파일:', '틀:', '나무위키:']):
            continue

        for region, keywords in REGIONAL_KEYWORDS.items():
            if any(kw in title or kw in raw_text[:300] for kw in keywords):
                text = clean_markup(raw_text)
                if len(text) < 100:
                    break
                if region not in results:
                    results[region] = []
                results[region].append({
                    'name': title,
                    'origin': region,
                    'description': text[:2000],
                    'habitats': [],
                    'weakness': '',
                    'source': 'namuwiki',
                })
                break

        if (i + 1) % 100000 == 0:
            total_found = sum(len(v) for v in results.values())
            print(f'  {i+1:,}/{total:,} 처리 중... (추출: {total_found}건)', flush=True)

    print('\n지역별 추출 결과:')
    for region, items in results.items():
        print(f'  {region}: {len(items)}건')

    # 기존 파일과 병합
    with open(YOKAI_PATH, encoding='utf-8') as f:
        existing = json.load(f)
    existing_names = {s['name'] for s in existing}

    new_items = []
    for items in results.values():
        for item in items:
            if item['name'] not in existing_names:
                new_items.append(item)
                existing_names.add(item['name'])

    merged = existing + new_items
    with open(YOKAI_PATH, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f'\n기존 {len(existing)}건 + 신규 {len(new_items)}건 = {len(merged)}건')
    print(f'저장 완료: {YOKAI_PATH}')

if __name__ == '__main__':
    run()
