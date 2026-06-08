"""
괴담 데이터 일괄 전처리:
1. 불량 데이터 제거 (게임/애니/만화/스포츠 등)
2. 마크업 정제
3. 지역 수정
"""
import json, re, os, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(BASE_DIR, 'database', 'data', 'verified_korean_horror_master.json')

# ── 제거할 제목 패턴 ──────────────────────────────────────────────────────────
REMOVE_TITLE = {
    # 게임
    'AK-630', 'AK-630M1-2', 'Abandon Lonliness', 'Chaos Orb',
    'Ben drowned', 'Book of the shadow',  # 이건 keep
    # 공포 아닌 개요/설명
    '괴담', '도시전설', '납량', '공포', '미스터리', '미신', '오컬트', '크리피파스타',
    '미스터리 갤러리', '미스터리 관련 정보', '한국 공포문학 단편선', '미스터리 텔러',
    # 스포츠 징크스
    '야구계의 저주들', '염소의 저주', '히칼도의 저주', '김성근의 저주',
    '선뮤직의 저주', '황금돼지해', '축구통제령', '레알 마드리드 10번의 저주',
    '펠레의 저주', '슈퍼맨의 저주',
    # 음식
    '지렁이 버거', '비둘기 꼬치', '유전자 조작 치킨', '모기 눈알 수프',
    '코카콜라의 도시전설', '짜장면 한 그릇을 시키면 침을 뱉는다',
    '다시 데우면 절대 안되는 음식', '탄 음식 발암물질설',
    '잡초 파전', '아기가 타고 있어요', '빵이 없으면 케이크를 먹으면 되지',
    '식품 관련 루머', 'IMF괴담', '바다거북 수프',
    # 과학/의학
    '수영하다 딸이 임신했다', '선인장의 전파 흡수 효과', '기침심폐소생술',
    '달라붙은 렌즈', '뱀에게서 살아남는 방법', '인간의 뇌는 10%만 사용된다',
    '체온손실은 대부분 머리에서 발생한다', '혀를 깨물면 죽는다',
    'Hysterical strength', '눈 뜨고 재채기하면 안구가 튀어나온다',
    '플랫 에러', '지진운', '초저주파', '하이랜더 증후군',
    # 역사/정치
    '배후중상설', '보르네오 고양이 공수 작전', '간첩 블로그', '쇠말뚝',
    '일제풍수모략설', '쿠미호',
    # 기타 불필요
    '황금귀', '납량', '경기고 축구부', '루리웹의 저주', '무한도전의 저주',
    '카더라 통신', '청량리 할머니', 'UFO 목격담 필수요소',
    '수능한파', '허경영 효과', '가갑선', 'ㅅ자가 들어가는 가수들',
    '가짜 악성코드 괴담', '구제역 괴담', '닭피 문신',
    '디시인사이드 정모 관련 괴담', '스위스 공업에 대한 도시전설',
    '코끼리 무덤', '클릭 잘못해서 입대', '파발꾼의 훈도시',
    '게이 폭탄', '원숭이술', '분재 고양이', '불고기 GP',
    '뱀 강도', '효도르의 저주', '애니멀 커뮤니케이터',
    '수박서리 괴담', '가수는 노래 따라간다',
    '자살하는 쥐', '병균우편물', '공자식인설',
    '소니타이머', '퇴마사', '토빈의 혼령도감',
    '* .wav 파일 열화 논란', '*.wav 파일 열화 논란', 'ZhUOZ',
    'FBI 심리테스트', '바트의 죽음', '히로빈',
    '징징이의 자살',
    # 성인
    '자궁섹스', '거제도 수간 사건', '귀신이 나오는 야동', '귀접', '아카다마', '섹스 포교',
    # 영화/만화
    '납골당의 미스터리', '네덜란드 구두 미스터리', '로마 모자 미스터리',
    '던위치의 공포', '프랑스 파우더 미스터리',
    '프랑켄슈타인의 저주', '명탐정의 저주',
}

# ── 내용 기반 제거 패턴 ──────────────────────────────────────────────────────
REMOVE_CONTENT = [
    'dc official App', 'window.OutLink', 'function()',
    '딸딸이', '포르노',
    '분류:스포츠', '분류:게임', '분류:음악', '분류:드라마',
    '분류:만화', '분류:애니메이션',
]

# ── 마크업 정제 ───────────────────────────────────────────────────────────────
def clean_content(text):
    text = re.sub(r'\[br\]', '\n', text)
    text = re.sub(r'\[\*([^\]]*)\]', r'\1', text)
    text = re.sub(r'~~([^~\n]*)~~', r'\1', text)
    text = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    text = re.sub(r'\|\|[^\n]*', '', text)
    text = re.sub(r'\[목차\]|\[clearfix\]|\[각주\]', '', text)
    text = re.sub(r'파일:[^\s\n\|]+', '', text)
    text = re.sub(r'width=\d+[^\s\n]*', '', text)
    text = re.sub(r'height=\d+[^\s\n]*', '', text)
    text = re.sub(r'align=[^\s\n]+', '', text)
    text = re.sub(r'={2,}[^=\n]+=*', '', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'</?\w+[^>]*>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()

# ── 지역 수정 ─────────────────────────────────────────────────────────────────
US_TITLES = {
    'Ben drowned', 'Jeff the Killer', 'Slenderman', 'Sonic.exe', 'username666',
    'barbie.avi', 'Entity 303', 'MOMO(괴담)', 'Eyeless Jack', 'I feel fantastic',
    'foundonthetape', 'EXE(크리피파스타)', '슬렌더맨', '슬렌더 패밀리',
    'Null(마인크래프트)', 'The midnight game', 'Three Kings',
    '폴리비우스', '필라델피아 실험', '케네디가의 저주', '링컨과 케네디의 공통점',
    '딥 웹', '마리아나 웹', '검은 눈 아이들', '디스맨',
    '하수구의 악어', '고양이 전자레인지', '멕시칸 펫', '베이비시터의 실수',
    '상향등 살인마', '침대 밑에 숨어있는 남자', '문 틈의 갈고리 손',
    '소니 빈', '스프링힐드 잭', '버뮤다 삼각지대', '크램푸스',
    '셰도우 맨', '당나귀 여인', '멜의 구멍', '디북 박스',
    '아미티빌의 저주', '라써타 인터뷰', '프로젝트 알파',
    '하수구의 악어', '코렁탕', '아크어드벤쳐',
    '초록색 아이들', '헨리 텐디', '미주리의 거미', '도마뱀 인간',
    '리자드 맨', '버닙', '더블린 호수의 괴물', '블루 타이거',
    '카사이 렉스', '데블 몽키', '에밀라 은투카', '즈바 포피',
    '브로스노 호수의 용', '칼카자가 산', '커널 샌더스의 저주',
    '폴 매카트니 사망설', '테쿰세의 저주',
    '프랜시스 베이컨의 냉동 닭', 'Alien big cat', '렙틸리언', '그레이(외계인)',
    '니비루', '일루미나티', 'The Most Mysterious Song on the Internet',
    '아포칼립스를 생존을 위한 10가지 행동지침',
    '검은 헬기', '메트로2', '게이 폭탄', '찰리찰리 챌린지',
    '아이도저', '아인슈타인의 예언', '하일브론의 유령', '뉴욕 지하철 괴담',
    '영국 지하철 실종사건',
}

JP_TITLES = {
    '나홀로 숨바꼭질', '나폴리탄 괴담', '테케테케', '쿠네쿠네', '히키코상',
    '도랸세', '토미노의 지옥', '카고메카고메', '하나이치몬메', '사라야시키',
    '붉은 방 사이트', '소의 목', '화장실의 하나코상', '틈새녀', '팔척귀신',
    '사령카페', '사메지마 사건', '사자에상의 집', '선탠 괴담', '로슈타인의 회랑',
    '옐로 피-포', '맛있는 라멘 가게', '말하는 목', '목 없는 라이더', '목 없는 말',
    '도쿄 디즈니랜드의 미아', '벚나무 아래에는', '방송이 끝난 뒤에는',
    '그녀는 온 세상에 있습니다', '타치바나 아유미', '교수의 메모',
    '나츠미 스텝 보너스', '나티', '오키나와에 지하철을 놓지 못하는 이유',
    '야와타노 야부시라즈', '이누나키 마을', '이누나키 터널', '미도로 연못',
    '고베의 단독주택', '일촌할멈', '손목 라멘 사건', '게 드럼통 욕조',
    '완장을 찬 소년', '스기사와 마을', '삿짱', '사토루 군', '야다 게이치로의 복수극',
    '키사라기역', '료멘스쿠나(도시전설)', '히에이는 그런 말 안 해',
    '코토리바코', '원숭이 꿈', '죽음의 편지 괴담', '정말로 있었다! 저주의 비디오',
    '가짜 기차', '가문에 흐르는 악의 피', '곰인형 출연자', '리카짱 전화',
    '아가야 열냥 벌러 가자', '보라색 거울',
    '콩콩콩귀신', '통벽귀신', '고인 전화번호 사용설',
    '일본국유철도 3대 미스터리 사건', '괴인 앤서', '탓수타 마루 호 침몰 사건',
}

def fix_region(s):
    title = s['title']
    content = s['content'][:500]
    region = s['region']
    if title in US_TITLES:
        return '미국'
    if title in JP_TITLES:
        return '일본'
    if region == '한국':
        if '일본의 도시전설' in content or '일본에서' in content[:200]:
            return '일본'
        if '미국에서' in content[:200] or '미국발' in content[:200]:
            return '미국'
    return region


def run():
    with open(PATH, encoding='utf-8') as f:
        stories = json.load(f)
    before = len(stories)
    print(f'시작: {before}건')

    # 1. 제목 기반 제거
    stories = [s for s in stories if s['title'] not in REMOVE_TITLE]
    print(f'제목 필터 후: {len(stories)}건')

    # 2. 내용 기반 제거
    stories = [s for s in stories if not any(kw in s['content'][:300] for kw in REMOVE_CONTENT)]
    print(f'내용 필터 후: {len(stories)}건')

    # 3. 마크업 정제
    for s in stories:
        s['content'] = clean_content(s['content'])

    # 4. 너무 짧아진 것 제거
    stories = [s for s in stories if len(s['content']) >= 80]
    print(f'80자 미만 제거 후: {len(stories)}건')

    # 5. 지역 수정
    for s in stories:
        s['region'] = fix_region(s)

    # 결과
    print(f'\n최종: {len(stories)}건 ({before - len(stories)}건 제거)')
    regions = Counter(s['region'] for s in stories)
    for r, c in regions.most_common():
        print(f'  {r}: {c}건')

    with open(PATH, 'w', encoding='utf-8') as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    print('\n저장 완료')


if __name__ == '__main__':
    run()
