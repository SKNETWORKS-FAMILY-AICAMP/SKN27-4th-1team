# 전처리 코드 실행 및 연결 기준

## 목적

`src/data-processing/processing` 폴더의 코드는 `database/data` 안의 원천 JSON을 분석하고, 필요한 파일만 `database/processed`에 전처리 결과로 저장한다.

현재 기본 목표는 **DCInside 수집 글만 전처리**하는 것이다. `verified_korean_horror_master.json`과 `ultimate_global_mythology_1000.json`은 나중에 다시 필요할 수 있으므로 코드에 남겨 두되 기본 실행 대상에서는 제외한다. `misin.json`은 PostgreSQL에 단순 적재하는 데이터라 전처리 대상에서 제외한다.

## 현재 원천 데이터

| 파일 | 현재 판단 | 전처리 기본 대상 |
| --- | --- | --- |
| `dcinside_horror_filtered.json` | 열린 게시판/검색/임베딩에 활용할 외부 수집 글 | 예 |
| `verified_korean_horror_master.json` | 검증된 괴담 데이터. 나중에 다시 전처리 가능 | 아니오 |
| `ultimate_global_mythology_1000.json` | 요괴/신화 엔티티 데이터. 나중에 다시 전처리 가능 | 아니오 |
| `misin.json` | 미신 문장 데이터. 현재는 단순 적재 대상 | 아니오 |

## 실행 순서

1. 원천 데이터 구조 분석

```bash
python src/data-processing/processing/analyze_raw_data.py
```

생성 파일:

```text
database/processed/raw_data_profile.md
```

2. 전처리 실행

```bash
python src/data-processing/processing/preprocess_data.py
```

기본 생성 파일:

```text
database/processed/dcinside_horror_processed.json
```

3. 전처리 결과 품질 검토

```bash
python src/data-processing/processing/check_processed_quality.py
```

생성 파일:

```text
database/processed/quality_report.md
```

## 코드 파일 역할

| 파일 | 역할 |
| --- | --- |
| `analyze_raw_data.py` | `database/data`의 JSON 구조, 결측치, 본문 후보, 노이즈 후보를 분석한다. `misin.json`은 제외한다. |
| `cleaning_rules.py` | 본문 정리 규칙과 노이즈 탐지 규칙을 관리한다. |
| `keyword_extractor.py` | 제목, 본문, 메타데이터를 기준으로 대표 키워드를 추출한다. |
| `preprocess_data.py` | 전처리 실행 파일이다. 기본적으로 DCInside만 처리한다. |
| `check_processed_quality.py` | processed 결과의 중복/반복 후보를 삭제하지 않고 리포트로 기록한다. |

## 처리 대상 변경 방법

기본값은 DCInside만 처리한다.

```python
PROCESS_DCINSIDE = True
PROCESS_VERIFIED = False
PROCESS_MYTHOLOGY = False
PROCESS_MISIN = False
```

나중에 검증 괴담 또는 요괴 데이터를 다시 전처리하려면 `preprocess_data.py`에서 아래 값만 바꾸면 된다.

```python
PROCESS_VERIFIED = True
PROCESS_MYTHOLOGY = True
```

`misin.json`은 현재 전처리 대상이 아니므로 `PROCESS_MISIN`은 그대로 `False`로 둔다.

## DCInside 전처리 기준

| 원본 컬럼 | 처리 방식 |
| --- | --- |
| `title` | `[경험]`, `[괴담]`, `[사건/사고]`, `[창작]` 태그를 분류값으로 사용한다. DB 적재 시 title 컬럼으로 저장하지 않는다. |
| `content` | 실제 본문으로 사용하고 URL, HTML, 마크다운 링크, 과한 공백을 정리한다. |
| `region` | 삭제하지 않고 metadata에 보존한다. |
| `source` | source와 document_id 생성 기준으로 사용한다. |

분류 기준:

| 원본 태그 | 저장 분류 |
| --- | --- |
| `[경험]` | `WITNESS` |
| `[괴담]` | `WITNESS` |
| `[사건/사고]` | `WITNESS` |
| `[창작]` | `CREATION` |

분류가 불명확하거나 본문이 비어 있는 행은 기본 전처리 결과에서 제외한다.
