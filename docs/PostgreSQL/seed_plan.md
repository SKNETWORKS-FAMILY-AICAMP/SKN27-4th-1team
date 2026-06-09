# PostgreSQL 초기 데이터 적재 계획

## 목적

이 문서는 `database/data` 폴더의 JSON 4개를 PostgreSQL 테이블에 어떻게 적재할지 정리한다.

실제 적재 스크립트는 다음 파일이다.

```text
database/PostgreSQL/import_json_data.py
```

## 적재 대상

| JSON 파일 | 대상 테이블 | 적재 여부 | 비고 |
| --- | --- | --- | --- |
| `database/data/verified_korean_horror_master.json` | `horror_stories` | 적재 | 검증 괴담/도시전설 |
| `database/data/ultimate_global_mythology_1000.json` | `myth_entities` | 적재 | 괴이/신화 존재 |
| `database/data/misin.json` | `superstitions` | 적재 | 미신/금기 문장 |
| `database/data/dcinside_horror_filtered.json` | `dcinside_posts` | 적재 | DCInside 수집 게시글 |

## 1. verified_korean_horror_master.json

대상 테이블:

```text
horror_stories
```

필드 매핑:

| JSON 필드 | DB 컬럼 | 처리 방식 |
| --- | --- | --- |
| `source` | `source` | 없으면 `verified_korean_horror_master` |
| 없음 | `source_ref_id` | `source + title + region + content` 기반 해시 |
| `title` | `title` | 그대로 저장 |
| 없음 | `language` | `ko` 고정 |
| `region` | `region` | 그대로 저장 |
| 없음 | `url` | 빈 문자열 |
| `content` | `preview` | 본문 앞부분으로 생성 |
| `content` | `content` | 그대로 저장 |
| 없음 | `category` | 빈 문자열 |
| 없음 | `metadata` | 빈 JSON |

중복 방지 기준:

```text
UNIQUE (source, source_ref_id)
```

## 2. ultimate_global_mythology_1000.json

대상 테이블:

```text
myth_entities
```

필드 매핑:

| JSON 필드 | DB 컬럼 | 처리 방식 |
| --- | --- | --- |
| 없음 | `source` | `ultimate_global_mythology_1000` 고정 |
| 없음 | `source_ref_id` | `source + name + origin` 기반 해시 |
| `name` | `name` | 그대로 저장 |
| `origin` | `origin` | 그대로 저장 |
| `description` | `description` | 그대로 저장 |
| 없음 | `behavior` | 빈 문자열 |
| `weakness` | `weakness` | 그대로 저장 |
| 없음 | `history` | 빈 문자열 |
| 없음 | `signs` | 빈 문자열 |
| 없음 | `survival_rules` | 빈 리스트 |
| `source` | `source_site` | 출처 문자열로 저장 |
| 없음 | `source_url` | 빈 문자열 |
| `habitats` | `metadata.habitats` | metadata에 보존 |

중복 방지 기준:

```text
UNIQUE (source, source_ref_id)
```

## 3. misin.json

대상 테이블:

```text
superstitions
```

필드 매핑:

| JSON 필드 | DB 컬럼 | 처리 방식 |
| --- | --- | --- |
| 없음 | `source` | `misin` 고정 |
| `id` | `source_ref_id` | 문자열로 저장 |
| `content` | `content` | 원문 그대로 저장 |
| 없음 | `category` | 빈 문자열 |
| 없음 | `region` | 빈 문자열 |
| 없음 | `metadata` | 빈 JSON |

중요 결정:

```text
misin.json은 taboos 테이블로 가공하지 않는다.
superstitions 테이블에 문장 원문 그대로 저장한다.
현재 pgvector 임베딩 대상에서는 제외한다.
```

## 4. dcinside_horror_filtered.json

대상 테이블:

```text
dcinside_posts
```

필드 매핑:

| JSON 필드 | DB 컬럼 | 처리 방식 |
| --- | --- | --- |
| `source` | `source` | 없으면 `dcinside_gongpow` |
| 없음 | `source_ref_id` | `source + title + region + content` 기반 해시 |
| `title` | `category` | `[창작]`은 `CREATION`, `[경험]`, `[괴담]`, `[사건/사고]`는 `WITNESS` |
| `title` + `content` | `title` | 원본 title이 태그뿐이면 content 앞부분으로 생성 |
| `region` | `region` | 없으면 `한국` |
| `content` | `content` | 그대로 저장 |
| 없음 | `metadata` | 원본 title 태그 저장 |
| 없음 | `is_active` | `true` |

중복 방지 기준:

```text
UNIQUE (source, source_ref_id)
```

## pgvector 임베딩 대상

초기 임베딩 대상은 아래 3개이다.

```text
horror_stories
myth_entities
dcinside_posts
```

`superstitions`와 사용자가 직접 작성하는 `post_post`는 현재 임베딩 대상에서 제외한다.

## 적재 후 확인 기준

현재 JSON 기준 예상 개수:

| 테이블 | 예상 개수 |
| --- | ---: |
| `horror_stories` | 325 |
| `myth_entities` | 604 |
| `superstitions` | 214 |
| `dcinside_posts` | 분류 가능한 DCInside row 수 |

적재 후 아래 쿼리 파일로 개수를 확인한다.

```text
database/PostgreSQL/queries/count_check.sql
```

## 실행 순서

볼륨 초기화 후 처음부터 다시 세팅한다면 아래 순서가 안전하다.

```powershell
docker compose down -v
docker compose up -d postgres
python manage.py migrate
python database\PostgreSQL\import_json_data.py
```

pgvector까지 이어서 실행할 경우:

```powershell
Get-Content database\PostgreSQL\pgvector\schema_pgvector.sql | docker compose exec -T postgres psql -U postgres -d goei_sillok
python database\PostgreSQL\pgvector\embed_records.py --reset
python database\PostgreSQL\pgvector\search_vectors.py "폐교 음악실 귀신"
```
