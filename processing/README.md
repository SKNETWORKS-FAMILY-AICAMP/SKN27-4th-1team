# 전처리 코드 실행 및 reference 연결

## 목적

`processing` 폴더의 코드는 원천 JSON 데이터를 분석하고, 본문을 정리하고, 대표 키워드를 추출한 뒤, 전처리 결과와 품질 검토 기록을 생성한다.

이 코드는 `reference` 폴더의 수업 노트북에서 다룬 데이터 클리닝, pandas 처리 흐름, NLP 전처리 개념을 현재 프로젝트 데이터 구조에 맞게 적용한 것이다.

## reference 반영 내용

| reference 파일 | 반영한 개념 | 연결된 코드 |
| --- | --- | --- |
| `2. Data Cleaning.ipynb` | 결측치 확인, 중복 확인, 문자열 정리, 정리 전/후 비교 | `analyze_raw_data.py`, `cleaning_rules.py`, `check_processed_quality.py` |
| `1. Pandas 기초.ipynb` | JSON/CSV 저장, records 형태 데이터 구성 | `preprocess_data.py` |
| `2. Pandas 심화.ipynb` | 컬럼 생성, 행별 처리 흐름, 조건 기반 처리 | `preprocess_data.py`, `check_processed_quality.py` |
| `2-1. Integer Encoding.ipynb` | 단어 빈도 기반 어휘 후보, 불용어 제외 | `keyword_extractor.py` |
| `2-2. 형태소 분석 & 어휘집 & Padding.ipynb` | 토큰화, 품사/명사 중심 후보 추출 흐름 | `keyword_extractor.py` |

현재 구현은 중첩 JSON 구조와 `metadata` 보존이 중요해서 pandas DataFrame 대신 표준 `json` 라이브러리와 함수형 처리 흐름을 사용한다. 다만 처리 개념은 reference의 pandas/전처리 흐름과 연결된다.

## 실행 순서

1. 원천 데이터 분석

```bash
python processing/analyze_raw_data.py
```

생성 파일:

```text
database/processed/raw_data_profile.md
```

2. 전처리 실행

```bash
python processing/preprocess_data.py
```

생성 파일:

```text
database/processed/thering_horror_processed.json
database/processed/ultimate_global_mythology_processed.json
database/processed/integrated_horror_processed.json
```

3. 전처리 결과 품질 검토

```bash
python processing/check_processed_quality.py
```

생성 파일:

```text
database/processed/quality_report.md
```

`raw_data_profile.json`과 `quality_report.json`은 기본 생성하지 않는다. 구조화된 JSON 리포트가 필요하면 각 스크립트의 옵션을 `True`로 바꿔 생성한다.

## 코드 파일 역할

| 파일 | 역할 |
| --- | --- |
| `analyze_raw_data.py` | 원천 JSON의 컬럼, 결측치, 본문 후보, 노이즈 후보, 키워드 후보를 분석한다. |
| `cleaning_rules.py` | 본문 정리 규칙과 노이즈 탐지 규칙을 관리한다. |
| `keyword_extractor.py` | 제목, 본문, 기존 키워드, 메타데이터를 이용해 대표 키워드를 추출한다. |
| `preprocess_data.py` | 전처리 정책에 따라 processed JSON 파일을 생성한다. |
| `check_processed_quality.py` | 전처리 결과의 중복/반복 후보를 삭제하지 않고 리포트로 기록한다. |

## 주요 처리 결정

- `thering_horror.json`은 `content`를 `description`으로 사용한다.
- `ultimate_global_mythology_1000.json`은 원본 `description`만 processed의 `description`에 넣는다.
- `behavior`, `history`, `signs`, `weakness`, `survival_rules`는 삭제하지 않고 `metadata`에 보존한다.
- `metadata` 값은 삭제하지 않고 반복 공백, 과도한 줄바꿈, URL, HTML 태그, 마크다운 링크 같은 명확한 문자열 노이즈만 가볍게 정리한다.
- `namu_asia_horror.json`은 `content`가 스크립트/로딩 노이즈로 판단되어 기본 전처리 대상에서 제외한다.
- 제목이 비슷한 문서는 바로 중복 삭제하지 않고 품질 검토 리포트에 후보로만 기록한다.
