# PostgreSQL 초기 데이터 적재 계획

## 목적

이 문서는 `docs/` 폴더의 JSON 원천 데이터를 PostgreSQL 테이블에 어떻게 넣을지 정리한다.

실제 적재 스크립트는 Django 모델 작성과 migration 이후에 작성한다.

## 적재 대상

| JSON 파일 | 대상 테이블 | 적재 여부 |
| --- | --- | --- |
| `docs/verified_korean_horror_master.json` | `horror_stories` | 적재 |
| `docs/ultimate_global_mythology_1000.json` | `myth_entities` | 적재 |
| `docs/misin.json` | `superstitions` | 적재 |
| `docs/global_horror_database.json` | 없음 | 제외 |

## 1. verified_korean_horror_master.json

대상 테이블:

```text
horror_stories
```

필드 매핑:

| JSON 필드 | DB 컬럼 | 처리 방식 |
| --- | --- | --- |
| `id` | `source_ref_id` | 문자열로 저장 |
| `source` | `source` | 그대로 저장 |
| `title` | `title` | 그대로 저장 |
| 없음 | `language` | 기본값 `ko` |
| `region` | `region` | 그대로 저장 |
| `url` | `url` | 그대로 저장 |
| 없음 | `preview` | `content` 앞부분으로 생성 |
| `content` | `content` | 그대로 저장 |
| `category` | `category` | 그대로 저장 |
| 기타 | `metadata` | 필요 시 원본 보존 |

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
| `id` | `source_ref_id` | 문자열로 저장 |
| `name` | `name` | 그대로 저장 |
| `origin` | `origin` | 그대로 저장 |
| `description` | `description` | 그대로 저장 |
| `behavior` | `behavior` | 그대로 저장 |
| `weakness` | `weakness` | 그대로 저장 |
| `history` | `history` | 그대로 저장 |
| `signs` | `signs` | 그대로 저장 |
| `survival_rules` | `survival_rules` | JSON 배열로 저장 |
| `source_site` | `source_site` | 그대로 저장 |
| `source_url` | `source_url` | 그대로 저장 |
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
| 없음 | `category` | NULL |
| 없음 | `region` | NULL |
| 없음 | `metadata` | 빈 JSON |

중요 결정:

```text
misin.json은 taboos 테이블로 가공하지 않는다.
superstitions 테이블에 문장 원문 그대로 저장한다.
```

중복 방지 기준:

```text
UNIQUE (source, source_ref_id)
```

## 적재 후 확인 기준

현재 JSON 기준 예상 개수:

| 테이블 | 예상 개수 |
| --- | ---: |
| `horror_stories` | 224 |
| `myth_entities` | 1016 |
| `superstitions` | 214 |

적재 후 `queries/count_check.sql`로 개수를 확인한다.

## 실제 실행 기록

아래 내용은 PostgreSQL 테이블 생성과 JSON 적재를 위해 실제 PowerShell 터미널에서 실행한 명령이다.

### 1. Django 모델 작성

ERD 기준으로 아래 파일에 모델을 작성했다.

```text
archive/models.py
generator/models.py
post/models.py
accounts/models.py
```

작성된 모델:

```text
archive.models.HorrorStory
archive.models.MythEntity
archive.models.Superstition
generator.models.GeneratedStory
post.models.Post
accounts.models.GeneratedStoryBookmark
accounts.models.PostBookmark
```

### 2. 필요한 Python 패키지 설치

처음 `makemigrations` 실행 시 PostgreSQL 드라이버가 없어 아래 오류가 발생했다.

```text
ModuleNotFoundError: No module named 'psycopg2'
```

`requirements.txt` 전체 설치도 시도했지만, `ragas` 의존성 중 `scikit-network`가 Windows C++ 빌드 도구를 요구해서 실패했다.

그래서 Django migration에 필요한 최소 패키지만 따로 설치했다.

```powershell
python -m pip install django==6.0.6 "psycopg[binary]==3.3.2"
```

설치 결과:

```text
Successfully installed django-6.0.6 psycopg-3.3.2 psycopg-binary-3.3.2
```

### 3. migration 파일 생성

PostgreSQL 서버가 아직 실행되지 않은 상태에서는 connection timeout 경고가 날 수 있어 `PGCONNECT_TIMEOUT`을 짧게 설정하고 실행했다.

```powershell
$env:PGCONNECT_TIMEOUT='2'; python manage.py makemigrations
```

생성된 migration 파일:

```text
archive/migrations/0001_initial.py
generator/migrations/0001_initial.py
post/migrations/0001_initial.py
accounts/migrations/0001_initial.py
```

### 4. Django 모델 검사

```powershell
python manage.py check
```

실행 결과:

```text
System check identified no issues (0 silenced).
```

### 5. 로컬 환경변수 파일 생성

Docker Compose와 Django 설정에 필요한 `.env` 파일이 없어서 `.env.example` 값을 기준으로 로컬 `.env`를 생성했다.

사용한 주요 값:

```text
POSTGRES_DB=goei_sillok
POSTGRES_USER=postgres
POSTGRES_PASSWORD=post1234
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

주의:

```text
.env는 .gitignore에 포함되어 있으므로 Git에는 올라가지 않는다.
```

### 6. PostgreSQL Docker 컨테이너 실행

```powershell
docker compose up -d postgres
```

실행 후 상태 확인:

```powershell
docker compose ps
```

확인 결과:

```text
goei_postgres   postgres:16   Up ... (healthy)   0.0.0.0:5432->5432/tcp
```

### 7. PostgreSQL에 실제 테이블 생성

Django migration을 PostgreSQL에 적용했다.

```powershell
python manage.py migrate
```

생성된 주요 테이블:

```text
auth_user
horror_stories
myth_entities
superstitions
generated_stories
post_post
generated_story_bookmarks
post_bookmarks
```

테이블 목록 확인:

```powershell
docker compose exec postgres psql -U postgres -d goei_sillok -c "\dt"
```

### 8. JSON 적재 스크립트 실행

아래 스크립트를 추가했다.

```text
database/PostgreSQL/import_json_data.py
```

실행 명령:

```powershell
python database/PostgreSQL/import_json_data.py
```

실행 결과:

```text
horror_stories: imported_or_updated=224
myth_entities: imported_or_updated=1016
superstitions: imported_or_updated=214
```

### 9. 적재 개수 확인

PowerShell에서는 `<` 리다이렉션이 동작하지 않으므로 `Get-Content`와 파이프를 사용했다.

```powershell
Get-Content -LiteralPath 'database\PostgreSQL\queries\count_check.sql' | docker compose exec -T postgres psql -U postgres -d goei_sillok
```

확인 결과:

```text
generated_stories          0
generated_story_bookmarks  0
horror_stories             224
myth_entities              1016
post_bookmarks             0
post_post                  0
superstitions              214
```

`generated_stories`, `post_post`, `bookmarks` 계열 테이블이 0인 것은 정상이다. 이 데이터는 사용자가 화면에서 글을 작성하거나 보관함에 저장해야 생성된다.

## 다음 단계

현재 PostgreSQL 테이블 생성과 원천 JSON 적재까지 완료되었다.

다음 작업은 화면 또는 Django view에서 이 테이블들을 조회하도록 연결하는 것이다.

```text
기록 열람실 -> horror_stories, myth_entities, superstitions 조회
금기 자료실 -> superstitions 조회
신규 기록실 -> generated_stories 생성
열린 게시판 -> post_post 생성/조회
나의 보관함 -> generated_story_bookmarks, post_bookmarks 조회
```

## 화면/사용자 행동별 저장 테이블

아래 표는 사이트에서 사용자가 어떤 행동을 했을 때 PostgreSQL의 어느 테이블에 저장되는지 정리한 것이다.

| 화면/행동 | 저장 또는 조회 테이블 | 설명 |
| --- | --- | --- |
| 회원가입 | `auth_user` | Django 기본 사용자 테이블에 계정 정보 저장 |
| 로그인 | `auth_user`, `django_session` | 사용자 인증은 `auth_user`, 로그인 세션은 `django_session` 사용 |
| 기록 열람실에서 괴담 조회 | `horror_stories` | JSON에서 적재한 한국 괴담/도시전설 데이터 조회 |
| 기록 열람실에서 괴이 존재 조회 | `myth_entities` | JSON에서 적재한 신화/전설/괴이 존재 데이터 조회 |
| 금기 자료실에서 미신/금기 문장 조회 | `superstitions` | `misin.json` 원문 문장 조회 |
| 신규 기록실에서 AI 괴담 저장 | `generated_stories` | 사용자가 입력한 조건과 AI 생성 결과 저장 |
| 열린 게시판에 글 작성 | `post_post` | 목격담/창작담 게시글 저장 |
| AI 생성 괴담을 나의 보관함에 저장 | `generated_story_bookmarks` | 사용자와 생성 괴담의 저장 관계 저장 |
| 열린 게시판 글을 나의 보관함에 저장 | `post_bookmarks` | 사용자와 게시글의 저장 관계 저장 |

## 주요 테이블별 저장 내용

### auth_user

회원가입한 사용자의 기본 계정 정보가 저장된다.

```text
username
password
email
last_login
date_joined
```

`password`는 원문 비밀번호가 아니라 Django가 해시 처리한 값으로 저장된다.

### django_session

로그인 상태를 유지하기 위한 세션 정보가 저장된다.

사용자가 로그인할 때마다 모든 정보가 `auth_user`에 새로 저장되는 것이 아니라, 로그인 유지 정보는 `django_session`이 담당한다.

### horror_stories

기록 열람실에서 보여줄 괴담/도시전설 원천 데이터가 저장된다.

대상 데이터:

```text
docs/verified_korean_horror_master.json
```

예시:

```text
장산범
빨간 마스크
구미호
도깨비
```

### myth_entities

신화, 전설, 괴이 존재 데이터가 저장된다.

대상 데이터:

```text
docs/ultimate_global_mythology_1000.json
```

예시:

```text
요괴
호문클루스
저지 데블
```

### superstitions

미신/금기 문장 데이터가 저장된다.

대상 데이터:

```text
docs/misin.json
```

중요:

```text
misin.json은 taboos로 가공하지 않고 superstitions에 원문 그대로 저장한다.
```

### generated_stories

신규 기록실에서 사용자가 입력한 조건과 AI가 생성한 괴담 결과가 저장된다.

저장 예시:

```text
user_id = 작성자
region = 충청북도 괴산
place = 폐교 음악실
entity_type = 귀신
taboo_text = 이름을 세 번 부르지 말 것
title = 생성된 괴담 제목
content = 생성된 괴담 본문
```

### post_post

열린 게시판에 사용자가 작성한 글이 저장된다.

저장 예시:

```text
user_id = 작성자
board_type = witness 또는 creation
title = 게시글 제목
region = 지역
content = 게시글 본문
view_count = 조회수
```

### generated_story_bookmarks

사용자가 AI 생성 괴담을 나의 보관함에 저장했을 때 사용된다.

저장 구조:

```text
user_id = 저장한 사용자
generated_story_id = 저장한 AI 생성 괴담
memo = 사용자 메모
```

즉, 생성 괴담 본문을 다시 복사해서 저장하는 테이블이 아니라, `generated_stories`를 참조하는 연결 테이블이다.

### post_bookmarks

사용자가 열린 게시판 글을 나의 보관함에 저장했을 때 사용된다.

저장 구조:

```text
user_id = 저장한 사용자
post_id = 저장한 게시글
memo = 사용자 메모
```

즉, 게시글 본문을 다시 복사해서 저장하는 테이블이 아니라, `post_post`를 참조하는 연결 테이블이다.

## Django 기본 관리 테이블

아래 테이블은 Django가 자동으로 생성하고 관리한다.

| 테이블 | 역할 |
| --- | --- |
| `auth_group` | 사용자 그룹 |
| `auth_permission` | 권한 정보 |
| `auth_group_permissions` | 그룹과 권한 연결 |
| `auth_user_groups` | 사용자와 그룹 연결 |
| `auth_user_user_permissions` | 사용자별 직접 권한 |
| `django_admin_log` | Django admin 작업 로그 |
| `django_content_type` | Django 모델 메타 정보 |
| `django_migrations` | 적용된 migration 기록 |
| `django_session` | 로그인 세션 |

이 테이블들은 서비스 화면의 핵심 데이터라기보다는 Django 인증, 권한, 관리자, migration, 세션 관리를 위한 기본 테이블이다.
# 현재 models.py 기준 테이블명 정리

ERD와 PostgreSQL 문서는 현재 Django `models.py`와 기존 migration 흐름을 우선해서 정리한다.

따라서 `Post`, `Like`, `Bookmark` 모델은 별도 `Meta.db_table`을 추가하지 않고 Django 기본 테이블명을 사용한다.

| 모델 | 실제 테이블명 | 설명 |
| --- | --- | --- |
| `post.Post` | `post_post` | 열린 게시판 게시글 |
| `post.Like` | `post_like` | 게시글 좋아요 기록 |
| `accounts.Bookmark` | `accounts_bookmark` | 외부/Neo4j 괴담 자료 보관 기록 |
| `generator.GeneratedStory` | `generated_stories` | AI 생성 괴담 |
| `accounts.GeneratedStoryBookmark` | `generated_story_bookmarks` | AI 생성 괴담 보관 기록 |
| `accounts.PostBookmark` | `post_bookmarks` | 게시글 보관 기록 |

이 결정에 맞춰 다음 파일도 현재 테이블명 기준으로 수정했다.

```text
docs/ERD/postgresql_erd_plan.md
docs/ERD/postgresql_erd_explanation.md
database/PostgreSQL/schema.sql
database/PostgreSQL/queries/count_check.sql
database/PostgreSQL/queries/sample_select.sql
database/PostgreSQL/import_json_data.py
```

현재 기준으로 카운트 확인 쿼리는 아래 테이블을 확인한다.

```text
horror_stories
myth_entities
superstitions
generated_stories
post_post
post_like
accounts_bookmark
generated_story_bookmarks
post_bookmarks
```

`import_json_data.py`는 원천 JSON 위치를 `database/data/`로 본다.

```powershell
python database/PostgreSQL/import_json_data.py
```
