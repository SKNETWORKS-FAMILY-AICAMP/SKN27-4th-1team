# 전처리 결과 품질 검토 리포트

이 리포트는 중복 후보를 삭제하지 않고 검토 대상으로만 기록한다.

## 요약

- 전체 문서 수: 2204
- dcinside_gongpow: 2204

## 처리 기록

### mythology 설명 필드 중복

- 발견 내용: 초기 전처리에서 description + behavior + history + signs + weakness를 단순 결합해 description 안에 이미 포함된 behavior/history/weakness 내용이 cleaned_text에 반복되는 문제가 발견되었다.
- 처리 내용: processed의 description에는 원본 description만 저장하도록 수정했다. behavior, history, signs, weakness, survival_rules는 삭제하지 않고 metadata에 보존했다.
- 결과: 수정 후 mythology 필드 중복 후보가 0개로 감소했다.

### 제목 유사 후보

- 발견 내용: thering 데이터에서 '<테두리 없는 거울> 계단의 하나코 - 1~完'처럼 제목이 유사한 문서가 발견되었다.
- 처리 내용: 본문 유사도가 낮고 회차가 다른 시리즈물이므로 중복 삭제 대상이 아니라 유지 대상으로 판단했다.
- 결과: 제목 유사 후보는 삭제하지 않고 검토 기록으로만 남긴다.

## document_id 중복

- 후보 수: 0

## source + source_id 중복

- 후보 수: 0

## url 중복

- 후보 수: 0

## title 중복

- 후보 수: 12
- 값: `안녕` / 개수: 2
  - `dcinside_gongpow_c465a1b0764b2e11` 안녕
  - `dcinside_gongpow_fa34e0d55577aa26` 안녕
- 값: `1` / 개수: 80
  - `dcinside_gongpow_47a82a5bd4620dd7` 1
  - `dcinside_gongpow_58a4c6a5208a3b9d` 1
  - `dcinside_gongpow_fda6d34dabea09a9` 1
  - `dcinside_gongpow_d856657277fb4cc8` 1
  - `dcinside_gongpow_2cf53087705bb2e6` 1
- 값: `4` / 개수: 2
  - `dcinside_gongpow_7534b088e0bbae94` 4
  - `dcinside_gongpow_4de6d969c3d58e98` 4
- 값: `안녕하세요` / 개수: 9
  - `dcinside_gongpow_78d7d189b891d9dd` 안녕하세요
  - `dcinside_gongpow_3f0601481d3f7acd` 안녕하세요
  - `dcinside_gongpow_cfc65e3b4437173c` 안녕하세요
  - `dcinside_gongpow_9f4404bc2df99450` 안녕하세요
  - `dcinside_gongpow_a380afa137b8c3f6` 안녕하세요
- 값: `귀신` / 개수: 2
  - `dcinside_gongpow_cf3c3461b6e34817` 귀신
  - `dcinside_gongpow_ab4cbe240984bfb3` 귀신
- 값: `고1때 사이비 같은 기독교 캠프 다녀온 썰 - 공포 마이너 갤러리 초6까` / 개수: 2
  - `dcinside_gongpow_33f85b1384fb1ce8` 고1때 사이비 같은 기독교 캠프 다녀온 썰 - 공포 마이너 갤러리 초6까
  - `dcinside_gongpow_cdaa5085776a5120` 고1때 사이비 같은 기독교 캠프 다녀온 썰 - 공포 마이너 갤러리 초6까
- 값: `시리즈 내가 어렸을 때 기억하기 싫은 기억 · 내가 어렸을 때 기억하` / 개수: 2
  - `dcinside_gongpow_fc641a68dd0ec5c5` [시리즈] 내가 어렸을 때 기억하기 싫은 기억 · 내가 어렸을 때 기억하
  - `dcinside_gongpow_89705291cc22a4ed` [시리즈] 내가 어렸을 때 기억하기 싫은 기억 · 내가 어렸을 때 기억하
- 값: `제목 없음` / 개수: 3
  - `dcinside_gongpow_47ef117f477777a7` 제목 없음
  - `dcinside_gongpow_b663a0bf7fbcfa2a` 제목 없음
  - `dcinside_gongpow_a7db987815b1cdd6` 제목 없음
- 값: `대학생 시절 이야기다` / 개수: 2
  - `dcinside_gongpow_ffa7f8b7c9145df4` 대학생 시절 이야기다
  - `dcinside_gongpow_35a9e02a1758f3eb` 대학생 시절 이야기다
- 값: `로어  출처를 알 수 없는 이야기 믿기 힘들지만 설득력 있는 이야기` / 개수: 48
  - `dcinside_gongpow_6446cb63cff44a75` 로어 : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있는 이야기,
  - `dcinside_gongpow_2c01df9538eb3034` 로어 : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있는 이야기,
  - `dcinside_gongpow_5e1740f5f254a71b` 로어 : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있는 이야기,
  - `dcinside_gongpow_0fbee9165391f4d4` 로어 : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있는 이야기,
  - `dcinside_gongpow_57e54cc9d4af035b` 로어 : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있는 이야기,
- 값: `로어lore  출처를 알 수 없는 이야기 믿기 힘들지만 설득력 있` / 개수: 4
  - `dcinside_gongpow_c9d799e36a903c91` 로어(Lore) : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있
  - `dcinside_gongpow_2b2731f9258fe445` 로어(Lore) : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있
  - `dcinside_gongpow_481a7006acf995da` 로어(Lore) : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있
  - `dcinside_gongpow_76c2a80c19bcfa4f` 로어(Lore) : 출처를 알 수 없는 이야기, 믿기 힘들지만 설득력 있
- 값: `----------------------------------------` / 개수: 7
  - `dcinside_gongpow_c7a2a68b49da6eed` ----------------------------------------
  - `dcinside_gongpow_3ab220cab0759c7f` ----------------------------------------
  - `dcinside_gongpow_2db60dbbde99636b` ----------------------------------------
  - `dcinside_gongpow_6a3fb5a5a9a677e1` ----------------------------------------
  - `dcinside_gongpow_c6de13bd59e85416` ----------------------------------------

## 문서 내부 반복 후보

- 후보 수: 4
- `dcinside_gongpow_212d51264f5f83db` 경기도 외곽, 자연보호구역과 인접한 언덕 위에 자리잡은 단독주택
  - 반복 2회: **[음성 인식 시도 중...]** **[인식 실패 - 99% 일치]** 여전히 99%였다.
- `dcinside_gongpow_9b264b324effa755` 이것은 이제 30살이 넘은 내가 체험했다고 할까, 아직도 체험하고 있는
  - 반복 2회: 그리고 아이를 낳을 때가 되어 크게 배가 부풀어 오른 그 아이의 어머니.
- `dcinside_gongpow_39708102101bd7c6` 눈보라가 온다는 소식을 들었어
  - 반복 2회: 그러자 눈은 창문위에 쌓여가기 시작했고, 우린 어둠속에 갇혔어.
  - 반복 2회: 내 동생인 지미는 눈이 더 쌓여서 천장이 무너지지는게 아닐까 두려워했어.
  - 반복 2회: 우린 럭키를 끝냈지만, 엄마는 꽤 오래전부터 더이상 먹지 않으셨어.
- `dcinside_gongpow_52156934b55eb740` 학교에 있는 폐건물 탐사하다 발견했는데 아무리 생각해봐도 피 같은데 알려
  - 반복 2회: : 네이버 블로그 (naver.com) 충격!; 미스터리 학교 내부 폐건물 탐사.

## mythology 필드 중복 후보

- 후보 수: 0

## 문서 간 유사 후보

- 후보 수: 0

## 제목 유사 후보

- 후보 수: 0

