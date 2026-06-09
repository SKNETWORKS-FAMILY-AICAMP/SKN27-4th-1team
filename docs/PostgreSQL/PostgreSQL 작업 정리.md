# PostgreSQL 작업 정리

## 목적

이 문서는 `database/data` 폴더의 현재 JSON 4개를 기준으로 PostgreSQL에 어떤 테이블로 적재할지, 어떤 컬럼을 살릴지, 이후 어떤 파일을 수정해야 하는지 정리한다.

현재 기준 JSON 파일은 다음 4개이다.

| 파일 | 레코드 수 | 주요 필드 | 적재 방향 |
|---|---:|---|---|
| `verified_korean_horror_master.json` | 325 | `title`, `content`, `region`, `source` | `horror_stories` |
| `ultimate_global_mythology_1000.json` | 604 | `name`, `origin`, `description`, `habitats`, `weakness`, `source` | `myth_entities` |
| `misin.json` | 214 | `id`, `content` | `superstitions` |
| `dcinside_horror_filtered.json` | 2204 | `title`, `content`, `region`, `source` | `dcinside_posts` |

## 현재 결론

기존 계획은 `verified_korean_horror_master`, `ultimate_global_mythology_1000`, `misin` 중심이었다.

이제는 `dcinside_horror_filtered.json`도 포함해야 하므로, PostgreSQL 적재 계획은 아래처럼 바꾸는 것이 좋다.

```text
검증 괴담 JSON -> horror_stories
세계 괴이/신화 JSON -> myth_entities
미신 JSON -> superstitions
DCInside 괴담 JSON -> dcinside_posts
```

DCInside 데이터는 사용자가 직접 작성한 게시글이 아니라 외부에서 수집한 게시판 데이터이다. 따라서 사용자 게시글 테이블인 `post_post`와 섞지 않고, 별도 테이블인 `dcinside_posts`로 분리하는 편이 더 명확하다.

이렇게 분리하면 `post_post`는 서비스 사용자가 작성한 열린 게시판 글만 담당하고, `dcinside_posts`는 외부 수집 데이터 또는 초기 참고 데이터 역할만 담당한다.

## 테이블별 적재 계획

### 1. `horror_stories`

대상 파일은 `verified_korean_horror_master.json`이다.

| JSON 필드 | DB 컬럼 | 처리 방식 |
|---|---|---|
| `source` | `source` | 없으면 `verified_korean_horror_master` |
| 자동 생성 | `source_ref_id` | 원본에 `id`가 없으므로 `source + title + content` 기반 해시 권장 |
| `title` | `title` | 그대로 저장 |
| 고정값 | `language` | `ko` |
| `region` | `region` | 그대로 저장, 없으면 빈 문자열 |
| 없음 | `url` | 빈 문자열 |
| `content` | `preview` | 본문 앞부분으로 자동 생성 |
| `content` | `content` | 그대로 저장 |
| 없음 | `category` | 빈 문자열 또는 `verified_horror` |
| 기타 | `metadata` | 필요 시 원본 보조 정보 저장 |

주의할 점은 현재 원본에 `id`가 없다는 것이다. 기존처럼 단순 순번을 `source_ref_id`로 쓰면 JSON 순서가 바뀌었을 때 중복 문제가 생길 수 있다. 가능하면 해시 기반 `source_ref_id`를 만드는 것이 안전하다.

### 2. `myth_entities`

대상 파일은 `ultimate_global_mythology_1000.json`이다.

| JSON 필드 | DB 컬럼 | 처리 방식 |
|---|---|---|
| `source` | `source` | 없으면 `ultimate_global_mythology_1000` |
| 자동 생성 | `source_ref_id` | `source + name + origin` 기반 해시 권장 |
| `name` | `name` | 그대로 저장 |
| `origin` | `origin` | 그대로 저장 |
| `description` | `description` | 그대로 저장 |
| 없음 | `behavior` | 현재 JSON에 없으므로 빈 문자열 |
| `weakness` | `weakness` | 그대로 저장 |
| 없음 | `history` | 빈 문자열 |
| 없음 | `signs` | 빈 문자열 |
| 없음 | `survival_rules` | 빈 리스트 |
| `source` | `source_site` | 원본 출처명 저장 |
| 없음 | `source_url` | 빈 문자열 |
| `habitats` | `metadata.habitats` | 리스트 형태로 metadata에 보존 |

현재 JSON은 예전 계획보다 필드가 줄어든 상태이다. `behavior`, `history`, `signs`, `survival_rules`, `source_url`은 원본에 없으므로 빈 값으로 처리하는 것이 맞다.

### 3. `superstitions`

대상 파일은 `misin.json`이다.

| JSON 필드 | DB 컬럼 | 처리 방식 |
|---|---|---|
| 고정값 | `source` | `misin` |
| `id` | `source_ref_id` | 문자열로 변환해서 저장 |
| `content` | `content` | 그대로 저장 |
| 없음 | `category` | 현재는 빈 문자열 |
| 없음 | `region` | 현재는 빈 문자열 |
| 없음 | `metadata` | 빈 JSON |

미신 데이터는 현재 pgvector 임베딩 대상이 아니다. PostgreSQL에는 단순 문장 데이터로 저장하고, 금기 자료실 화면이나 검색 필터가 생기면 그때 category/region 분리를 고민한다.

### 4. `dcinside_posts`

대상 파일은 `dcinside_horror_filtered.json`이다.

이 파일은 사용자 작성 게시글이 아니므로 `post_post`가 아니라 별도 테이블인 `dcinside_posts`에 저장한다.

| JSON 필드 | DB 컬럼 | 처리 방식 |
|---|---|---|
| `source` | `source` | 없으면 `dcinside_gongpow` |
| 자동 생성 | `source_ref_id` | `source + title + content` 기반 해시 권장 |
| `title` | `category` | `[창작]`이면 `CREATION`, `[경험]`, `[괴담]`, `[사건/사고]`이면 `WITNESS` |
| `title` + `content` | `title` | `title`이 태그뿐이면 `content` 앞부분으로 제목 생성 |
| `region` | `region` | 없으면 `한국` |
| `content` | `content` | 본문 저장 |
| 없음 | `metadata` | 원본 title 태그 등 보조 정보 저장 |
| 없음 | `is_active` | 화면 노출 여부, 기본값 `true` |
| 자동 생성 | `created_at` | Django `auto_now_add` 또는 DB 기본값 |

DCInside 데이터에서 살릴 필드는 `title`, `content`, `region`, `source`이다.

`dcinside_posts`에는 `source`, `source_ref_id`를 반드시 두는 것이 좋다. 그래야 import 스크립트를 여러 번 실행해도 같은 수집글이 중복 저장되지 않는다.

목록 화면에서 보여줄 짧은 미리보기 문장은 별도 컬럼으로 저장하지 않는다. `content`에서 필요한 길이만 잘라서 화면에서 처리한다.

## DCInside 데이터 처리 기준

DCInside의 `title` 값은 실제 제목이라기보다 분류 태그인 경우가 많다.

예시:

```text
[경험]
[괴담]
[사건/사고]
[창작]
```

따라서 아래 기준으로 처리하는 것이 좋다.

| 원본 title | 저장 category | 저장 title 처리 |
|---|---|---|
| `[창작]` | `CREATION` | 본문 앞 30자 정도로 제목 생성 |
| `[경험]` | `WITNESS` | 본문 앞 30자 정도로 제목 생성 |
| `[괴담]` | `WITNESS` | 본문 앞 30자 정도로 제목 생성 |
| `[사건/사고]` | `WITNESS` | 본문 앞 30자 정도로 제목 생성 |
| 그 외 실제 제목 | 태그 판단 불가 시 `WITNESS` 또는 건너뛰기 | 원본 제목 사용 |

추천 기준은 다음과 같다.

```text
1차 적재에서는 알 수 없는 title은 건너뛰기
확실한 태그만 WITNESS / CREATION으로 분리
본문이 비어 있거나 너무 짧은 데이터는 건너뛰기
```

이렇게 해야 열린 게시판에 품질이 낮은 데이터가 섞이는 것을 줄일 수 있다.

## 수정이 필요한 파일 계획

현재는 문서 기준 계획이며, 실제 반영 시 아래 파일들을 수정해야 한다.

| 파일 | 수정 이유 | 수정 내용 |
|---|---|---|
| `archive/models.py` | DCInside 전용 테이블 추가 | `DcinsidePost` 모델 추가 |
| `database/PostgreSQL/schema.sql` | ERD/SQL 기준 업데이트 | `dcinside_posts` CREATE TABLE 추가 |
| `database/PostgreSQL/import_json_data.py` | 4개 JSON 전체 적재 | `import_dcinside_posts()` 함수 추가 |
| `database/PostgreSQL/queries/count_check.sql` | 적재 검증 | `dcinside_posts` 개수와 category별 개수 확인 쿼리 추가 |
| `database/PostgreSQL/queries/sample_select.sql` | 화면 검증 | 열린 게시판 목격담/창작담 조회 샘플 추가 |
| `docs/ERD/postgresql_erd_explanation.md` | ERD 설명 최신화 | `dcinside_posts` 테이블 설명 추가 |

## `dcinside_posts` 신규 테이블 계획

DCInside 데이터를 안정적으로 import하려면 사용자 게시글 테이블인 `post_post`를 수정하기보다 `dcinside_posts` 테이블을 새로 두는 것이 좋다.

권장 컬럼은 다음과 같다.

| 컬럼 | 타입 | 이유 |
|---|---|---|
| `id` | `BIGSERIAL` | 내부 PK |
| `source` | `VARCHAR(100)` | 데이터 출처가 `dcinside_gongpow`인지 구분 |
| `source_ref_id` | `VARCHAR(100)` | 같은 원본 글을 중복 적재하지 않기 위한 식별값 |
| `category` | `VARCHAR(15)` | `WITNESS` 또는 `CREATION` |
| `title` | `VARCHAR(200)` | 화면에 보여줄 제목 |
| `region` | `VARCHAR(100)` | 지역 표시 |
| `content` | `TEXT` | 원문 본문 |
| `metadata` | `JSONB` | 원본 title 태그 등 보조 정보 |
| `is_active` | `BOOLEAN` | 화면 노출 여부 |
| `created_at` | `TIMESTAMPTZ` | 적재 시각 |

권장 SQL 구조는 다음과 같다.

```sql
CREATE TABLE dcinside_posts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL DEFAULT 'dcinside_gongpow',
    source_ref_id VARCHAR(100) NOT NULL,
    category VARCHAR(15) NOT NULL,
    title VARCHAR(200) NOT NULL,
    region VARCHAR(100) DEFAULT '한국',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ,
    UNIQUE (source, source_ref_id)
);
```

이렇게 하면 사용자 작성글은 `post_post`에 남기고, 외부 수집글은 `dcinside_posts`에 분리할 수 있다.

## pgvector와의 연결 계획

현재 pgvector 임베딩 대상은 아래 3개로 한다.

```text
horror_stories
myth_entities
dcinside_posts
```

DCInside 게시글은 `record_embeddings.source_table = 'dcinside_posts'`로 저장한다.

`superstitions`는 PostgreSQL에는 저장하지만 현재 임베딩 대상에서는 제외한다.

검색 대상 역할은 다음과 같다.

```text
horror_stories: 검증 괴담/도시전설 검색
myth_entities: 괴이/신화 존재 검색
dcinside_posts: DCInside 수집 게시글 검색
```

## 최종 실행 순서 계획

볼륨 초기화 후 처음부터 다시 세팅한다면 순서는 아래가 안전하다.

```powershell
docker compose down -v
docker compose up -d postgres
python manage.py makemigrations
python manage.py migrate
python database\PostgreSQL\import_json_data.py
docker compose exec postgres psql -U postgres -d goei_sillok -c "\dt"
```

pgvector까지 이어서 실행할 경우:

```powershell
Get-Content database\PostgreSQL\pgvector\schema_pgvector.sql | docker compose exec -T postgres psql -U postgres -d goei_sillok
python database\PostgreSQL\pgvector\embed_records.py --reset
python database\PostgreSQL\pgvector\search_vectors.py "폐교 음악실 귀신"
```

## 이번 변경의 핵심

이번 계획 변경의 핵심은 삭제된 JSON을 제외하고, 현재 남아 있는 4개 JSON만 PostgreSQL 적재 대상으로 다시 정의하는 것이다.

가장 중요한 결정은 `dcinside_horror_filtered.json`을 `horror_stories`나 `post_post`에 섞지 않고 `dcinside_posts`로 분리하는 것이다.

이렇게 해야 사용자 작성 게시글을 저장하는 `post_post`의 역할이 흐려지지 않고, 외부 수집 데이터도 별도 테이블에서 안정적으로 관리할 수 있다.
