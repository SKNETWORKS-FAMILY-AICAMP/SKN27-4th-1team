# 전처리 결과 품질 검토 리포트

이 리포트는 중복 후보를 삭제하지 않고 검토 대상으로만 기록한다.

## 요약

- 전체 문서 수: 1061
- Wikipedia: 1016
- thering: 45

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

- 후보 수: 0

## 문서 내부 반복 후보

- 후보 수: 0

## mythology 필드 중복 후보

- 후보 수: 0

## 문서 간 유사 후보

- 후보 수: 0

## 제목 유사 후보

- 후보 수: 19
- `thering_2278` / `thering_2276` title=0.957, text=0.244
  - <테두리 없는 거울> 계단의 하나코 - 完
  - <테두리 없는 거울> 계단의 하나코 - 5
- `thering_2278` / `thering_2275` title=0.957, text=0.257
  - <테두리 없는 거울> 계단의 하나코 - 完
  - <테두리 없는 거울> 계단의 하나코 - 4
- `thering_2278` / `thering_2274` title=0.957, text=0.109
  - <테두리 없는 거울> 계단의 하나코 - 完
  - <테두리 없는 거울> 계단의 하나코 - 3
- `thering_2278` / `thering_2268` title=0.957, text=0.317
  - <테두리 없는 거울> 계단의 하나코 - 完
  - <테두리 없는 거울> 계단의 하나코 - 2
- `thering_2278` / `thering_2267` title=0.957, text=0.273
  - <테두리 없는 거울> 계단의 하나코 - 完
  - <테두리 없는 거울> 계단의 하나코 - 1
- `thering_2276` / `thering_2275` title=0.957, text=0.408
  - <테두리 없는 거울> 계단의 하나코 - 5
  - <테두리 없는 거울> 계단의 하나코 - 4
- `thering_2276` / `thering_2274` title=0.957, text=0.136
  - <테두리 없는 거울> 계단의 하나코 - 5
  - <테두리 없는 거울> 계단의 하나코 - 3
- `thering_2276` / `thering_2268` title=0.957, text=0.35
  - <테두리 없는 거울> 계단의 하나코 - 5
  - <테두리 없는 거울> 계단의 하나코 - 2
- `thering_2276` / `thering_2267` title=0.957, text=0.404
  - <테두리 없는 거울> 계단의 하나코 - 5
  - <테두리 없는 거울> 계단의 하나코 - 1
- `thering_2275` / `thering_2274` title=0.957, text=0.119
  - <테두리 없는 거울> 계단의 하나코 - 4
  - <테두리 없는 거울> 계단의 하나코 - 3
- `thering_2275` / `thering_2268` title=0.957, text=0.245
  - <테두리 없는 거울> 계단의 하나코 - 4
  - <테두리 없는 거울> 계단의 하나코 - 2
- `thering_2275` / `thering_2267` title=0.957, text=0.436
  - <테두리 없는 거울> 계단의 하나코 - 4
  - <테두리 없는 거울> 계단의 하나코 - 1
- `thering_2274` / `thering_2268` title=0.957, text=0.268
  - <테두리 없는 거울> 계단의 하나코 - 3
  - <테두리 없는 거울> 계단의 하나코 - 2
- `thering_2274` / `thering_2267` title=0.957, text=0.191
  - <테두리 없는 거울> 계단의 하나코 - 3
  - <테두리 없는 거울> 계단의 하나코 - 1
- `thering_2268` / `thering_2267` title=0.957, text=0.328
  - <테두리 없는 거울> 계단의 하나코 - 2
  - <테두리 없는 거울> 계단의 하나코 - 1
- `wikipedia_172` / `wikipedia_479` title=0.957, text=0.411
  - Al (folklore)
  - Alp (folklore)
- `wikipedia_461` / `wikipedia_615` title=0.923, text=0.566
  - Merlin
  - Merlion
- `wikipedia_636` / `wikipedia_1008` title=0.909, text=0.576
  - Winged horse
  - Wind Horse
- `wikipedia_670` / `wikipedia_671` title=0.958, text=0.72
  - Wicked Witch of the West
  - Wicked Witch of the East

