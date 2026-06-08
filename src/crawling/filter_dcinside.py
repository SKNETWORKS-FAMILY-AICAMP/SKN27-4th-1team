"""
dcinside_horror.json 필터링 및 전처리
- 광고/스팸 제거
- 건의글([건의]) 제거
- 공포와 무관한 짧은 글 제거
- 중복 내용 제거
- 이모지 제거 (제목/내용 모두)
출력: database/data/dcinside_horror_filtered.json
"""
import json, re, os, sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT = os.path.join(BASE_DIR, 'database', 'data', 'dcinside_horror.json')
OUTPUT = os.path.join(BASE_DIR, 'database', 'data', 'dcinside_horror_filtered.json')

# 이모지 패턴
EMOJI_RE = re.compile(
    '[\U00010000-\U0010ffff'
    '\U00002600-\U000027ff'
    '\U0001F000-\U0001FFFF'
    '\U00002702-\U000027B0'
    '\U0000FE00-\U0000FE0F'
    '\U00003030]',
    flags=re.UNICODE
)

# 명백한 스팸/광고 패턴
SPAM_PATTERNS = [
    r'(https?://\S+).{0,50}(구매|주문|할인|이벤트|쿠폰|무료체험)',
    r'카카오톡\s*(id|ID|아이디)\s*[:：]\s*\S+',
    r'텔레그램\s*@\S+',
    r'오픈채팅\s*(링크|주소)',
    r'(비트코인|이더리움|코인).{0,30}(수익|투자|거래)',
]

# 공포 관련 키워드
HORROR_KEYWORDS = [
    '귀신', '유령', '저승', '공포', '무섭', '섬뜩', '소름',
    '가위눌', '환청', '환영', '이상하', '느낌이', '기분이',
    '괴담', '흉가', '묘지', '제사', '조상', '꿈에서', '악몽',
    '빙의', '무속', '점쟁이', '푸닥거리',
    '살인', '시체', '죽었', '죽음', '사망', '자살',
    '발소리', '문소리', '벽소리',
    '원혼', '혼령', '저주', '신내림',
    '갑자기', '느낌',
]

HORROR_RE = re.compile('|'.join(re.escape(k) for k in HORROR_KEYWORDS))
SPAM_RE = [re.compile(p) for p in SPAM_PATTERNS]


def remove_emoji(text):
    return EMOJI_RE.sub('', text).strip()


def is_spam(text):
    return any(p.search(text) for p in SPAM_RE)


def has_horror(text):
    return bool(HORROR_RE.search(text))


def filter_item(d):
    title = d.get('title', '')
    content = d.get('content', '')
    combined = title + ' ' + content

    # 건의글 제거
    if '건의' in title:
        return False, '건의글'

    # 너무 짧은 것 제거
    if len(content) < 100:
        return False, '너무짧음'

    # 명백한 스팸
    if is_spam(combined):
        return False, '스팸'

    # 공포 키워드 없고 짧은 경우 제거
    if len(content) < 300 and not has_horror(combined):
        return False, '비주제(짧음)'

    return True, 'ok'


def run():
    with open(INPUT, encoding='utf-8') as f:
        data = json.load(f)

    print(f'입력: {len(data)}건')

    results = []
    reasons = {}
    seen_contents = set()

    for d in data:
        keep, reason = filter_item(d)
        if not keep:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        # 중복 내용 제거
        content_key = d.get('content', '')[:200]
        if content_key in seen_contents:
            reasons['중복'] = reasons.get('중복', 0) + 1
            continue
        seen_contents.add(content_key)

        # 이모지 제거
        d['title'] = remove_emoji(d.get('title', ''))
        d['content'] = remove_emoji(d.get('content', ''))

        results.append(d)

    print(f'제거: {len(data) - len(results)}건')
    for r, cnt in reasons.items():
        print(f'  - {r}: {cnt}건')
    print(f'유지: {len(results)}건')

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'저장: {OUTPUT}')


if __name__ == '__main__':
    run()
