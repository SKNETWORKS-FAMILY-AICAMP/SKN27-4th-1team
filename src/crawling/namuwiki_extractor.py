"""
나무위키 parquet 파일을 직접 다운받아 괴담/요괴 문서를 추출한다.

출력:
    database/data/verified_korean_horror_master.json  <- 괴담 (Story)
    database/data/ultimate_global_mythology_1000.json <- 요괴/전설 (Legend/Yokai)
"""

import json
import re
import os
import sys
import urllib.request
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'database', 'data')
PARQUET_PATH = os.path.join(DATA_DIR, 'namuwiki.parquet')
PARQUET_URL = 'https://huggingface.co/api/datasets/heegyu/namuwiki/parquet/default/train/0.parquet'


# ── 카테고리 필터 ──────────────────────────────────────────────────────────────

STORY_CATEGORIES = {
    '괴담', '도시전설', '납량', '목격담', '오컬트',
    '귀신 이야기', '유령 이야기', '공포 이야기', '공포체험',
    '한국의 괴담', '일본의 괴담', '도시전설/한국', '도시전설/일본',
    '한국의 도시전설', '일본의 도시전설', '크리피파스타',
    '미확인생물체', '미확인 생물체',
}

YOKAI_CATEGORIES = {
    '한국의 요괴', '일본의 요괴', '중국의 요괴', '아시아의 요괴',
    '한국 신화', '일본 신화', '중국 신화', '동아시아 신화',
    '한국의 전설적 동물', '일본의 전설적 동물',
    '한국의 민속', '일본의 민속',
    '크립티드', '미확인생물', '전설의 생물/동아시아',
    '귀신', '도깨비', '구미호',
    # 추가 지역
    '필리핀의 요괴', '필리핀 신화', '동남아시아의 요괴', '동남아시아 신화',
    '태국의 요괴', '태국 신화', '인도의 요괴', '인도 신화', '힌두 신화',
    '티베트 신화', '네팔 신화', '불교 신화',
    '중국의 신', '중국의 전설', '서양의 요괴', '북유럽 신화',
    '그리스 신화', '켈트 신화', '슬라브 신화',
}

STORY_TITLE_KEYWORDS = [
    '괴담', '도시전설', '귀신', '유령', '혼령', '저주', '목격담',
    '공포', '오컬트', '폴터가이스트', '납량', '미스터리',
]

YOKAI_TITLE_KEYWORDS = [
    '요괴', '도깨비', '구미호', '이무기', '불가사리', '해태',
    '삼족오', '텐구', '카파', '갓파', '오니', '유키온나',
    '쿠치사케온나', '아마비에', '설녀', '자시키와라시',
    '장산범', '처녀귀신', '달걀귀신', '물귀신', '원귀',
    '야차', '나찰', '두억시니', '이매망량',
]

EXCLUDE_TITLE_PATTERNS = [
    r'^[#&@\d]',
    r'\(게임\)', r'\(애니메이션\)', r'\(만화\)', r'\(드라마\)',
    r'\(음악\)', r'\(앨범\)', r'\(노래\)', r'\(캐릭터\)', r'\(소설\)',
]

REGION_MAP = {
    '서울': ['서울', '한강', '명동', '강남', '홍대', '종로', '이태원', '마포'],
    '인천': ['인천', '송도', '부평'],
    '부산': ['부산', '해운대', '광안리', '남포동'],
    '대구': ['대구', '동성로'],
    '대전': ['대전', '둔산', '유성'],
    '광주': ['광주'],
    '울산': ['울산'],
    '경기': ['수원', '성남', '고양', '용인', '파주', '평택', '의정부'],
    '강원': ['강릉', '춘천', '원주', '속초', '설악', '동해', '강원'],
    '충청': ['청주', '천안', '충북', '충남', '세종'],
    '전라': ['전주', '목포', '여수', '순천', '전북', '전남'],
    '경상': ['경주', '포항', '창원', '진주', '경북', '경남', '안동'],
    '제주': ['제주', '한라산', '서귀포'],
    '일본': ['일본', '도쿄', '교토', '오사카', '홋카이도', '오키나와'],
    '중국': ['중국', '베이징', '상하이', '홍콩'],
    '미국': ['미국', '뉴욕', '로스앤젤레스'],
    '인도': ['인도', '힌두'],
    '필리핀': ['필리핀'],
    '태국': ['태국'],
}

ORIGIN_MAP = {
    '한국': ['한국', '조선', '고려', '신라', '백제', '고구려'],
    '일본': ['일본', '에도', '헤이안'],
    '중국': ['중국', '중화'],
    '인도': ['인도', '힌두'],
    '필리핀': ['필리핀'],
    '태국': ['태국'],
    '티베트/네팔': ['티베트', '네팔'],
    '서양': ['유럽', '그리스', '로마', '북유럽', '켈트', '슬라브'],
}


def download_parquet():
    token = os.getenv('HF_TOKEN', '')
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    print(f"parquet 다운로드 중... (2.9GB)")
    req = urllib.request.Request(PARQUET_URL, headers=headers)

    # 리디렉션 따라가서 실제 CDN URL로 다운로드
    with urllib.request.urlopen(req, timeout=30) as r:
        actual_url = r.url
        total = int(r.headers.get('Content-Length', 0))
        downloaded = 0
        chunk = 1024 * 1024 * 10  # 10MB
        with open(PARQUET_PATH, 'wb') as f:
            while True:
                buf = r.read(chunk)
                if not buf:
                    break
                f.write(buf)
                downloaded += len(buf)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.1f}% ({downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB)", end='', flush=True)
    print(f"\n다운로드 완료: {PARQUET_PATH}")


def extract_categories(text):
    return {c.strip() for c in re.findall(r'\[\[분류:([^\]]+)\]\]', text)}


def clean_markup(text):
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'={2,}.*?={2,}', '', text)
    text = re.sub(r'\[(?:include|youtube|anchor)[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r"'''?", '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'^ *[\*\|#>]+ *', '', text, flags=re.MULTILINE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def is_excluded(title):
    return any(re.search(p, title) for p in EXCLUDE_TITLE_PATTERNS)


def classify(title, raw_text):
    cats = extract_categories(raw_text)
    if cats & STORY_CATEGORIES:
        return 'story'
    if cats & YOKAI_CATEGORIES:
        return 'yokai'
    if any(title == kw or title.startswith(kw) for kw in YOKAI_TITLE_KEYWORDS):
        return 'yokai'
    if any(kw in title for kw in STORY_TITLE_KEYWORDS):
        return 'story'
    return None


def extract_region(title, text):
    combined = title + ' ' + text[:500]
    for region, keywords in REGION_MAP.items():
        if any(kw in combined for kw in keywords):
            return region
    return '한국'


def extract_origin(title, text):
    combined = title + ' ' + text[:500]
    for origin, keywords in ORIGIN_MAP.items():
        if any(kw in combined for kw in keywords):
            return origin
    return '기타'


def run():
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("pyarrow 설치 필요: pip install pyarrow")
        sys.exit(1)

    # 파일 없으면 다운로드
    if not os.path.exists(PARQUET_PATH):
        download_parquet()
    else:
        print(f"기존 파일 사용: {PARQUET_PATH}")

    print("parquet 읽는 중...")
    table = pq.read_table(PARQUET_PATH)
    titles = table['title'].to_pylist()
    texts = table['text'].to_pylist()
    total = len(titles)
    print(f"총 {total:,}건 처리 시작")

    stories, yokais, seen = [], [], set()

    for i, (title, raw_text) in enumerate(zip(titles, texts)):
        if not title or not raw_text:
            continue
        if any(title.startswith(p) for p in ['분류:', '파일:', '틀:', '나무위키:']):
            continue
        if title in seen or is_excluded(title):
            continue

        doc_type = classify(title, raw_text)
        if not doc_type:
            continue

        text = clean_markup(raw_text)
        if len(text) < 200:
            continue

        seen.add(title)
        if doc_type == 'story':
            stories.append({
                'title': title,
                'content': text[:3000],
                'region': extract_region(title, text),
                'source': 'namuwiki',
            })
        else:
            yokais.append({
                'name': title,
                'origin': extract_origin(title, text),
                'description': text[:2000],
                'habitats': [],
                'weakness': '',
                'source': 'namuwiki',
            })

        if (i + 1) % 50000 == 0:
            print(f"  {i+1:,}/{total:,} 처리 중... (괴담: {len(stories)}, 요괴: {len(yokais)})")

    print(f"\n추출 완료: 괴담 {len(stories)}건, 요괴/전설 {len(yokais)}건")

    story_path = os.path.join(DATA_DIR, 'verified_korean_horror_master.json')
    yokai_path = os.path.join(DATA_DIR, 'ultimate_global_mythology_1000.json')

    with open(story_path, 'w', encoding='utf-8') as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    print(f"저장: {story_path}")

    with open(yokai_path, 'w', encoding='utf-8') as f:
        json.dump(yokais, f, ensure_ascii=False, indent=2)
    print(f"저장: {yokai_path}")


if __name__ == '__main__':
    run()
