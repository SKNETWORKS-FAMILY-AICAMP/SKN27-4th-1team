"""
preprocessed_scp.json 후처리
- 잘못된 korean_name 정리
- object_class 정규화
"""
import json, re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(BASE_DIR, 'processing', 'preprocessed_scp.json')

CLASS_MAP = {
    '안전(Safe)': '안전', '유클리드(Euclid)': '유클리드', '케테르(Keter)': '케테르',
    '타우미엘(Thaumiel)': '타우미엘', '무효(Neutralized)': '무효', '난해(Esoteric)': '난해',
    'Safe': '안전', 'Euclid': '유클리드', 'Keter': '케테르',
    'Thaumiel': '타우미엘', 'Neutralized': '무효',
}

BAD_PREFIXES = ('저자:', '역자:', '원작:', '일련번호:', '등급:', 'http', 'F.A.Q', '+', 'x')
BAD_CONTAINS = ('일련번호', '등급:', '저자:', '역자:', '원작:')


def clean_korean_name(name):
    if not name:
        return ''
    if name.startswith(BAD_PREFIXES):
        return ''
    if any(p in name for p in BAD_CONTAINS):
        return ''
    # 한국어+영어 혼합 → 한국어 부분만
    m = re.search(r'\s+[A-Z][a-z]', name)
    if m and m.start() > 2:
        name = name[:m.start()].strip()
    # '영어: 한국어' → 한국어만
    if re.match(r'^[A-Za-z].*?:', name):
        parts = name.split(':', 1)
        if len(parts) == 2 and parts[1].strip():
            name = parts[1].strip()
    if name.startswith('(') or len(name) > 50 or len(name) < 2:
        return ''
    return name.strip()


def run():
    with open(PATH, encoding='utf-8') as f:
        data = json.load(f)

    print(f'입력: {len(data)}건')
    name_fixed = class_fixed = 0

    for d in data:
        original = d.get('korean_name', '')
        cleaned = clean_korean_name(original)
        if cleaned != original:
            d['korean_name'] = cleaned
            name_fixed += 1

        cls = d.get('object_class', '')
        normalized = CLASS_MAP.get(cls, cls)
        if '  ' in normalized:
            parts = [p.strip() for p in normalized.split() if p.strip()]
            normalized = parts[-1] if parts else normalized
        if normalized != cls:
            d['object_class'] = normalized
            class_fixed += 1

    print(f'korean_name 수정: {name_fixed}건')
    print(f'object_class 정규화: {class_fixed}건')

    with open(PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('저장 완료')


if __name__ == '__main__':
    run()
