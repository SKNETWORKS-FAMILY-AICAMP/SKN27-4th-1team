# PostgreSQL pgvector 임베딩 작업 계획

## 목적

PostgreSQL에 저장된 괴담/괴이/금기/게시글 텍스트를 임베딩 벡터로 변환해 의미 기반 검색을 할 수 있게 만든다.

기존 PostgreSQL 테이블은 원본 데이터 저장을 담당하고, pgvector는 검색용 임베딩 인덱스를 담당한다.

## 작업 범위

이번 작업은 PostgreSQL 안에서 pgvector 기반 검색을 준비하는 것이다.

포함:

- pgvector 확장 활성화
- 임베딩 저장 테이블 설계
- 원천 텍스트 수집 대상 결정
- 문장/문단 기반 청크 기준 결정
- 임베딩 생성 스크립트 작성 계획
- 유사도 검색 SQL/API 연결 계획

제외:

- Neo4j 그래프 관계 탐색
- Neo4j 벡터 인덱스 작업
- 화면 UI 수정
- LLM 답변 생성 로직

## 참고 자료

강의자료는 사용법과 예제 흐름을 참고한다.

| 파일 | 참고할 내용 |
| --- | --- |
| `1-1. PostgreSQL - pgvector.ipynb` | pgvector 기본 개념, extension, vector 컬럼, 유사도 검색 |
| `1-2. PostgreSQL - CustomPGVector.ipynb` | 커스텀 pgvector 테이블/검색 구조 |
| `1. PGVectorDB.ipynb` | RAG 구조 안에서 pgvector가 맡는 역할 |

주의:

강의자료의 DB 이름, 계정, 테이블 구조는 실습용이다. 이 프로젝트에서는 `goei_sillok` DB와 현재 Django 모델/테이블 구조에 맞춰 적용한다.

## 기본 방향

기존 테이블에 직접 `embedding` 컬럼을 추가하지 않고, 별도 임베딩 테이블을 만든다.

이유:

- 여러 원본 테이블을 하나의 벡터 검색 대상으로 합칠 수 있다.
- 원본 테이블 구조를 덜 건드린다.
- 청크 단위로 여러 embedding을 저장할 수 있다.
- 나중에 임베딩 모델이나 청크 기준을 바꿔도 재생성이 쉽다.

## 임베딩 대상 테이블

1차 대상은 아래 테이블로 한다.

| 원본 테이블 | 임베딩 대상 텍스트 | 청크 필요성 |
| --- | --- | --- |
| `horror_stories` | `title`, `region`, `category`, `preview`, `content` | 높음 |
| `myth_entities` | `name`, `origin`, `description`, `behavior`, `weakness`, `history`, `signs`, `survival_rules` | 중간 |
| `post_post` | `title`, `region`, `body`, `category` | 글 길이에 따라 다름 |

초기 MVP에서는 `horror_stories`, `myth_entities`를 먼저 임베딩한다.

`superstitions`는 현재 검색 대상에서 제외하기로 했으므로 pgvector 임베딩을 만들지 않는다.

`post_post`는 사용자가 계속 작성/수정/삭제하는 데이터이므로, 2차 단계에서 연결한다.

## 임베딩 저장 테이블 초안

테이블명:

```text
record_embeddings
```

컬럼 초안:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | bigserial PK | 임베딩 row id |
| `source_table` | varchar(100) | 원본 테이블명 |
| `source_id` | bigint | 원본 row id |
| `chunk_index` | integer | 같은 원본 row 안에서 몇 번째 chunk인지 |
| `title` | text | 검색 결과 표시용 제목 |
| `content` | text | 실제 임베딩한 chunk 텍스트 |
| `embedding` | vector(768) | 임베딩 벡터 |
| `metadata` | jsonb | 원본 카테고리, 지역, URL 등 부가 정보 |
| `created_at` | timestamptz | 생성 시각 |
| `updated_at` | timestamptz | 갱신 시각 |

중복 방지 기준:

```text
UNIQUE (source_table, source_id, chunk_index)
```

## 임베딩 모델 기준

API 쿼터 문제를 피하고 로컬에서 안정적으로 실행하기 위해 multilingual-e5-base 임베딩 모델을 사용한다.

```text
intfloat/multilingual-e5-base
```

이 모델의 임베딩 차원은 768이다.

따라서 pgvector 컬럼은 아래처럼 잡는다.

```sql
embedding vector(768)
```

장점:

- 다국어 검색용 모델이라 한국어 유사도 검색에도 사용할 수 있다.
- 외부 API 쿼터 제한 없이 로컬에서 실행할 수 있다.
- `sentence-transformers`로 바로 로딩할 수 있어 코드가 단순하다.
- 768차원이라 1024차원 모델보다 저장공간과 검색 부담이 줄어든다.


## 청크 기준

글자 수로만 자르면 문장 중간이 끊길 수 있다.

따라서 문장/문단 기반 청크를 사용한다.

기본 원칙:

1. 먼저 문단 기준으로 나눈다.
2. 문단이 너무 길면 문장 기준으로 다시 나눈다.
3. 문장들을 묶어서 목표 길이에 가까운 chunk를 만든다.
4. 다음 chunk에는 이전 chunk의 마지막 문장 1개를 겹쳐 넣는다.

초기 기준:

| 항목 | 값 |
| --- | ---: |
| 목표 chunk 길이 | 900자 |
| 최대 chunk 길이 | 1200자 |
| 최소 chunk 길이 | 80자 |
| overlap | 이전 chunk 마지막 문장 1개 |

문장 분리 기준:

```text
. ? ! … 다. 요. 니다. 습니다.
```

주의:

처음부터 완벽한 한국어 형태소 분석기를 붙이지 않는다. 먼저 정규식 기반으로 구현하고, 검색 품질이 부족하면 개선한다.

## 추천 파일 구조

```text
database/PostgreSQL/pgvector/
├─ pgvector_plan.md
├─ README.md
├─ schema_pgvector.sql
├─ embed_records.py
├─ search_vectors.py
├─ semantic_chunker.py
└─ queries/
   ├─ enable_extension.sql
   ├─ count_embeddings.sql
   └─ sample_vector_search.sql
```

각 파일 역할:

| 파일 | 역할 |
| --- | --- |
| `pgvector_plan.md` | 전체 계획 |
| `README.md` | 실행 순서 |
| `schema_pgvector.sql` | extension, 테이블, 인덱스 생성 SQL |
| `semantic_chunker.py` | 문장/문단 기반 청크 함수 |
| `embed_records.py` | 원본 테이블 조회, 청크 생성, 임베딩 저장 |
| `search_vectors.py` | 검색어 임베딩 후 유사도 검색 테스트 |
| `queries/*.sql` | DBeaver/psql에서 확인할 SQL |

## 단계별 작업 계획

### 1단계. Docker PostgreSQL 이미지 확인

현재 `docker-compose.yaml`의 PostgreSQL 이미지는 아래와 같다.

```yaml
image: postgres:16
```

일반 `postgres:16` 이미지에는 pgvector 확장이 없을 수 있다.

필요하면 아래 이미지로 변경한다.

```yaml
image: pgvector/pgvector:pg16
```

주의:

이미 DB 볼륨에 데이터가 있는 상태이므로 이미지 변경 전에는 백업/재생성 여부를 결정해야 한다.

### 2단계. pgvector 확장 활성화

DB 안에서 아래 SQL을 실행한다.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

확인 SQL:

```sql
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

### 3단계. 임베딩 테이블 생성

`record_embeddings` 테이블을 만든다.

초기에는 SQL 파일로 만든다.

나중에 Django 모델로 관리할지, SQL 전용 테이블로 둘지는 별도 결정한다.

### 4단계. 청크 함수 작성

`semantic_chunker.py`에 문장/문단 기반 청크 함수를 만든다.

입력:

```text
title
content
chunk_size
overlap
```

출력:

```python
[
    {"chunk_index": 0, "content": "..."},
    {"chunk_index": 1, "content": "..."},
]
```

### 5단계. 원본 데이터 수집 함수 작성

`embed_records.py`에서 아래 원본들을 읽는다.

```text
horror_stories
myth_entities
```

각 테이블별로 임베딩할 텍스트 조합을 정한다.

예:

```text
horror_stories:
제목 + 지역 + 카테고리 + 본문
```

### 6단계. 임베딩 생성

모델:

```text
intfloat/multilingual-e5-base
```

실행 방식:

- 한 번에 전체를 처리하지 않는다.
- batch 단위로 처리한다.
- 이미 저장된 `(source_table, source_id, chunk_index)`는 upsert한다.
- e5 계열 권장 방식에 맞춰 문서에는 `passage:` prefix, 검색어에는 `query:` prefix를 붙인다.

### 7단계. 유사도 검색 SQL 작성

검색 쿼리 예시:

```sql
SELECT
    source_table,
    source_id,
    chunk_index,
    title,
    content,
    1 - (embedding <=> %s::vector) AS similarity
FROM record_embeddings
ORDER BY embedding <=> %s::vector
LIMIT 10;
```

처음에는 Python 테스트 스크립트 `search_vectors.py`로 검색을 확인한다.

### 8단계. 검색 품질 확인

테스트 검색어 예시:

```text
폐교 음악실 귀신
비 오는 날 금기
도깨비 약점
이름을 부르면 나타나는 괴담
터널에서 들리는 목소리
```

확인 기준:

- 검색 결과가 의미상 비슷한가
- 너무 긴 chunk가 그대로 노출되지 않는가
- 같은 원본 row의 chunk가 과도하게 많이 뜨지 않는가
- `horror_stories`, `myth_entities`가 의미에 맞게 검색되는가

### 9단계. Django 서비스 연결

검색 스크립트가 안정화된 뒤 Django 서비스로 옮긴다.

후보 파일:

```text
archive/services/vector_search.py
```

예상 역할:

```text
검색어 입력
-> 검색어 임베딩
-> record_embeddings 유사도 검색
-> source_table/source_id 기준으로 원본 데이터 조회
-> 화면/API 응답 반환
```

### 10단계. 문서화

실행 순서를 `README.md`에 정리한다.

최소 포함 내용:

```text
1. Docker PostgreSQL 실행
2. pgvector extension 확인
3. schema 생성
4. 임베딩 적재 실행
5. 검색 테스트 실행
6. DBeaver 확인 SQL
```

## 예상 실행 순서

초안:

```powershell
docker compose up -d postgres
docker compose ps

# pgvector extension/table 생성
Get-Content database\PostgreSQL\pgvector\schema_pgvector.sql | docker compose exec -T postgres psql -U postgres -d goei_sillok

# 임베딩 적재
python database\PostgreSQL\pgvector\embed_records.py --reset

# 검색 테스트
python database\PostgreSQL\pgvector\search_vectors.py "폐교 음악실 귀신"
```

## 미결정 사항

| 항목 | 선택지 | 현재 의견 |
| --- | --- | --- |
| PostgreSQL 이미지 | `postgres:16` 유지 vs `pgvector/pgvector:pg16` 변경 | pgvector 이미지 권장 |
| 임베딩 테이블 관리 | Django 모델 vs SQL 전용 | 초기에는 SQL 전용 권장 |
| 임베딩 대상 | 원천 2종만 vs `post_post` 포함 | 1차 `horror_stories`, `myth_entities`, 2차 `post_post` |
| 청크 방식 | 글자 수 기준 vs 문장/문단 기준 | 문장/문단 기준 |
| 임베딩 모델 | MiniLM 384차원 vs Ollama qwen3 1024차원 vs Gemini 768/1024차원 vs KURE-v1 1024차원 vs e5-base 768차원 | `intfloat/multilingual-e5-base` 사용 |
| 화면 연결 | 기록 열람실 검색 vs 별도 테스트 API | 먼저 스크립트 검색 테스트 |


## 주의 사항

- pgvector 컬럼 차원은 임베딩 모델 차원과 반드시 일치해야 한다.
- 모델을 바꾸면 기존 `record_embeddings`는 재생성해야 한다.
- 긴 글은 반드시 chunk 단위로 임베딩한다.
- 원본 테이블의 본문을 직접 수정하지 않는다.
- Neo4j 임베딩과 PostgreSQL pgvector 임베딩은 역할이 다르다.
- 대량 임베딩은 시간이 걸릴 수 있으므로 batch 처리와 재실행 가능 구조가 필요하다.
