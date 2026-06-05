# 원천 데이터 프로파일

이 문서는 원천 JSON을 전처리하기 전에 데이터 상태를 분석한 결과이다.
원본 데이터는 수정하지 않았다.

## namu_asia_horror.json

- 데이터 개수: 128
- 추천 본문 상태: `needs_recrawl`
- 컬럼 수: 14

### 본문 후보 컬럼

| 컬럼 | 비어있지 않은 행 | 평균 길이 | 평균 한글 | 평균 영문 | 주요 노이즈 |
| --- | ---: | ---: | ---: | ---: | --- |
| `content` | 128 | 2693 | 0 | 1847.83 | hash_symbol, slash_symbol, square_brackets, citation_numbers, script_or_dom_noise, css_noise |

### 키워드 추출 후보

- 제목 컬럼: `title`
- 기존 키워드/태그 컬럼: `tags`
- 메타데이터 후보 컬럼: `habitat`, `origin`, `primary_type`, `region`, `source`, `tags`

### metadata 품질 분석

| 컬럼 | 비어있지 않은 행 | 평균 길이 | 주요 노이즈 | 샘플 |
| --- | ---: | ---: | --- | --- |
| `habitat` | 8 | 2.38 | slash_symbol | ["산악"] |
| `origin` | 0 | 0 | - |  |
| `primary_type` | 128 | 4.01 | slash_symbol | "도시전설" |
| `region` | 128 | 2.19 | slash_symbol | "한국" |
| `source` | 128 | 9 | - | "namu_wiki" |
| `tags` | 128 | 3.07 | slash_symbol | ["도시전설", "한국", "산악"] |

### 컬럼 요약

| 컬럼 | 타입 | 비어있지 않은 행 | 샘플 |
| --- | --- | ---: | --- |
| `ability` | {"list": 128} | 0 |  |
| `content` | {"str": 128} | 128 | "try{switch(JSON.parse(localStorage.getItem(\"theseed_settings\")||\"{}\")[\"wiki.theme\"]){case void 0:case\"auto\":var e,a=matchMedia(\"(prefers-color-scheme: dark)\");a" |
| `danger` | {"null": 128} | 0 |  |
| `form` | {"null": 128} | 0 |  |
| `gender` | {"null": 126, "str": 2} | 2 | "여성" |
| `habitat` | {"list": 128} | 8 | ["산악"] |
| `id` | {"int": 128} | 128 | 1 |
| `origin` | {"null": 128} | 0 |  |
| `primary_type` | {"str": 128} | 128 | "도시전설" |
| `region` | {"str": 128} | 128 | "한국" |
| `source` | {"str": 128} | 128 | "namu_wiki" |
| `tags` | {"list": 128} | 128 | ["도시전설", "한국", "산악"] |
| `title` | {"str": 128} | 128 | "장산범" |
| `url` | {"str": 128} | 128 | "https://namu.wiki/w/%EC%9E%A5%EC%82%B0%EB%B2%94" |

## thering_horror.json

- 데이터 개수: 45
- 추천 본문 상태: `valid_text`
- 컬럼 수: 18

### 본문 후보 컬럼

| 컬럼 | 비어있지 않은 행 | 평균 길이 | 평균 한글 | 평균 영문 | 주요 노이즈 |
| --- | ---: | ---: | ---: | ---: | --- |
| `content` | 45 | 500.53 | 328 | 25 | slash_symbol, square_brackets, markdown_links, urls |

### 키워드 추출 후보

- 제목 컬럼: `title`
- 기존 키워드/태그 컬럼: `keywords`
- 메타데이터 후보 컬럼: `category`, `country`, `horror_level`, `source`, `subcategory`

### metadata 품질 분석

| 컬럼 | 비어있지 않은 행 | 평균 길이 | 주요 노이즈 | 샘플 |
| --- | ---: | ---: | --- | --- |
| `category` | 45 | 4 | - | "실화괴담" |
| `country` | 45 | 2 | - | "한국" |
| `horror_level` | 45 | 1 | - | 3 |
| `source` | 45 | 7 | - | "thering" |
| `subcategory` | 45 | 3.82 | - | "교통도로" |

### 컬럼 요약

| 컬럼 | 타입 | 비어있지 않은 행 | 샘플 |
| --- | --- | ---: | --- |
| `category` | {"str": 45} | 45 | "실화괴담" |
| `comment_count` | {"int": 45} | 45 | 7 |
| `comments` | {"list": 45} | 45 | [{"author": "달려야", "date": "2017/02/07 00:18", "text": "하니...", "is_secret": false}, {"author": "홍", "date": "2017/02/07 13:18", "text": "오싹하네요.", "is_secret": false}] |
| `content` | {"str": 45} | 45 | "함께 일했던 여직원에게 들은 이야기입니다. 그 친구가 아는 분이 밤늦게 일행과 함께 차를 타고 어디론가 가고 있었다고 했습니다. 그게 고속도로인지 국도인지는 너무 오래전에 들은 이야기라 기억이 정확하지 않네요. 시각은 새벽쯤이었고 차 안에는 친구의 지인인 운전자와 친구들 세 명이 타고 " |
| `content_length` | {"int": 45} | 45 | 601 |
| `country` | {"str": 45} | 45 | "한국" |
| `date` | {"str": 45} | 45 | "2017-02-06" |
| `date_raw` | {"str": 45} | 45 | "2017/02/06 23:59" |
| `has_image` | {"bool": 45} | 45 | false |
| `horror_level` | {"int": 45} | 45 | 3 |
| `id` | {"int": 45} | 45 | 2326 |
| `keywords` | {"list": 45} | 42 | ["무서", "피", "소름", "비명"] |
| `series_number` | {"int": 37, "null": 8} | 37 | 572 |
| `source` | {"str": 45} | 45 | "thering" |
| `subcategory` | {"str": 45} | 45 | "교통도로" |
| `submitter` | {"null": 9, "str": 36} | 36 | "반가운 유저" |
| `title` | {"str": 45} | 45 | "당신에게도 일어난 무서운 이야기 제572화 - 고속도로" |
| `url` | {"str": 45} | 45 | "http://thering.co.kr/2326" |

## ultimate_global_mythology_1000.json

- 데이터 개수: 1016
- 추천 본문 상태: `valid_text`
- 컬럼 수: 12

### 본문 후보 컬럼

| 컬럼 | 비어있지 않은 행 | 평균 길이 | 평균 한글 | 평균 영문 | 주요 노이즈 |
| --- | ---: | ---: | ---: | ---: | --- |
| `behavior` | 1016 | 209.53 | 0 | 161.81 | hash_symbol, slash_symbol, square_brackets, extra_whitespace |
| `description` | 1016 | 420.97 | 137.21 | 177.66 | hash_symbol, slash_symbol, square_brackets, extra_whitespace |
| `history` | 1016 | 83.9 | 61.53 | 0 | slash_symbol |
| `signs` | 1016 | 36.36 | 26.35 | 0 | - |
| `weakness` | 1016 | 37.2 | 22.14 | 3.1 | - |

### 키워드 추출 후보

- 제목 컬럼: `name`
- 기존 키워드/태그 컬럼: 없음
- 메타데이터 후보 컬럼: `habitats`, `origin`, `source_site`

### metadata 품질 분석

| 컬럼 | 비어있지 않은 행 | 평균 길이 | 주요 노이즈 | 샘플 |
| --- | ---: | ---: | --- | --- |
| `habitats` | 1016 | 5.51 | slash_symbol | ["고대 유적지", "역사의 뒤안길", "미지의 영역"] |
| `origin` | 1016 | 8.9 | slash_symbol | "전 세계 전설/신화" |
| `source_site` | 1016 | 9 | - | "Wikipedia" |

### 컬럼 요약

| 컬럼 | 타입 | 비어있지 않은 행 | 샘플 |
| --- | --- | ---: | --- |
| `behavior` | {"str": 1016} | 1016 | "In cryptozoology and ufology, \"rods\" (also known as \"skyfish\", \"air rods\", or \"solar entities\") are elongated visual artifacts appearing in photographic images " |
| `description` | {"str": 1016} | 1016 | "Rod (optical phenomenon)은(는) 전 세계 전설/신화에 기록된 역사적이고 고증된 미스터리한 오컬트 존재입니다. 행동은 In cryptozoology and ufology, \"rods\" (also known as \"skyfish\", \"air rods\", or \"solar" |
| `habitats` | {"list": 1016} | 1016 | ["고대 유적지", "역사의 뒤안길", "미지의 영역"] |
| `history` | {"str": 1016} | 1016 | "전 세계 전설/신화에서 기원한 전설적인 존재로, 고대 문헌 및 구전 설화를 통해 오늘날까지 그 기이한 흔적이 전해져 내려오는 역사적인 변칙 엔티티입니다." |
| `id` | {"int": 1016} | 1016 | 1 |
| `name` | {"str": 1016} | 1016 | "Rod (optical phenomenon)" |
| `origin` | {"str": 1016} | 1016 | "전 세계 전설/신화" |
| `signs` | {"str": 1016} | 1016 | "공간의 기압이 변화하며 느껴지는 영적인 압박감, 이명 현상" |
| `source_site` | {"str": 1016} | 1016 | "Wikipedia" |
| `source_url` | {"str": 1016} | 1016 | "https://en.wikipedia.org/wiki/Rod_%28optical_phenomenon%29" |
| `survival_rules` | {"list": 1016} | 1016 | ["Rod (optical phenomenon)의 상세한 외관이나 관측 기록을 종이에 손으로 수기 작성하거나 음성 디바이스로 녹음하지 마십시오.", "Rod (optical phenomenon)의 오컬트 주파수에 노출되어 기이한 이명이나 환각 증상이 나타난다면 결계 정화 소금을 물에 타서 양치질을 거행하십시오.", "Rod (optical phenomenon)의 고대 사원 또는 지표면에 반쯤 묻혀 있는 역사적 금속물에 도구를 가져대어 충격을 가하거나 반출하지 마십시오."] |
| `weakness` | {"str": 1016} | 1016 | "고대의 연금술적 무기, 은(Silver) 제 도구, 정직하고 흔들림 없는 마음" |

