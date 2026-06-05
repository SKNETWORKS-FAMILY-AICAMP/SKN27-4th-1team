# PostgreSQL ERD 설명

## 1. 문서 목적

이 문서는 `postgresql_erd_plan.md`의 ERD를 더 쉽게 이해하기 위한 설명서다.

ERD 그림만 보면 테이블 이름과 관계는 보이지만, 각 테이블에 어떤 데이터가 들어가는지, 왜 필요한지, 어떤 화면에서 쓰이는지까지는 바로 알기 어렵다. 이 문서는 그 부분을 정리한다.

## 2. 전체 구조

PostgreSQL은 서비스 화면에서 직접 저장하고 조회해야 하는 데이터를 담당한다.

```text
회원
기록 열람실 원천 데이터
AI 생성 괴담
열린 게시판
좋아요
나의 보관함
```

Neo4j는 지역, 장소, 괴이, 금기 사이의 그래프 관계를 담당한다. 그래서 PostgreSQL에는 별도 `regions` 테이블을 만들지 않고, 필요한 화면 표시용 지역명만 문자열 컬럼으로 둔다.

## 3. 전체 테이블 요약

PostgreSQL에는 우리가 직접 설계한 서비스 테이블과 Django가 자동으로 관리하는 기본 테이블이 함께 생성된다.

그래서 DBeaver 같은 DB 도구에서 보면 테이블 수가 ERD 핵심 테이블보다 많아 보일 수 있다.

| 구분 | 테이블명 | 생성 주체 | 역할 | 주요 사용 위치 |
| --- | --- | --- | --- | --- |
| Django 기본 | `auth_user` | Django | 사용자 계정 정보 | 로그인, 회원가입, 작성자, 보관함 소유자 |
| Django 기본 | `auth_group` | Django | 사용자 그룹 정보 | 권한 관리 |
| Django 기본 | `auth_permission` | Django | 권한 목록 | 권한 관리 |
| Django 기본 | `auth_group_permissions` | Django | 그룹과 권한 연결 | 권한 관리 |
| Django 기본 | `auth_user_groups` | Django | 사용자와 그룹 연결 | 권한 관리 |
| Django 기본 | `auth_user_user_permissions` | Django | 사용자별 직접 권한 연결 | 권한 관리 |
| Django 기본 | `django_admin_log` | Django | 관리자 화면 작업 기록 | Django admin |
| Django 기본 | `django_content_type` | Django | 앱/모델 메타 정보 | Django 내부 관리 |
| Django 기본 | `django_migrations` | Django | 적용된 migration 기록 | DB 변경 이력 관리 |
| Django 기본 | `django_session` | Django | 로그인 세션 정보 | 로그인 유지 |
| archive | `horror_stories` | 직접 설계 | 한국 괴담 원천 데이터 | 기록 열람실 |
| archive | `myth_entities` | 직접 설계 | 신화/괴이 존재 데이터 | 기록 열람실 |
| archive | `superstitions` | 직접 설계 | 미신/금기 문장 데이터 | 금기 자료실 |
| generator | `generated_stories` | 직접 설계 | AI 생성 괴담과 입력 조건 | 신규 기록실, 나의 보관함 |
| post | `post_post` | Django 모델 기본명 | 열린 게시판 게시글 | 열린 게시판 |
| post | `post_like` | Django 모델 기본명 | 게시글 좋아요 기록 | 열린 게시판 |
| accounts | `accounts_bookmark` | Django 모델 기본명 | 외부/Neo4j 괴담 자료 보관 | 나의 보관함 |
| accounts | `generated_story_bookmarks` | 직접 설계 | AI 생성 괴담 보관 연결 | 나의 보관함 |
| accounts | `post_bookmarks` | 직접 설계 | 게시글 보관 연결 | 나의 보관함 |

핵심 서비스 테이블은 아래 9개다.

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

Django 기본 테이블은 서비스 기능을 직접 표현하는 테이블이라기보다는 인증, 권한, 세션, migration 관리를 위해 자동 생성되는 기반 테이블이다.

## 4. 테이블별 설명

### auth_user

Django 기본 사용자 테이블이다.

회원가입하면 사용자 ID, 비밀번호 해시, 이메일 등이 이 테이블에 저장된다. 우리가 직접 `users` 테이블을 새로 만들지 않는 이유는 Django 인증 기능을 그대로 쓰기 위해서다.

사용 위치:

- 로그인
- 회원가입
- 게시글 작성자
- AI 생성 괴담 작성자
- 보관함 소유자
- 좋아요 누른 사용자

### horror_stories

한국 괴담 원천 데이터를 저장하는 테이블이다.

기록 열람실에서 검색하거나 목록으로 보여줄 괴담 데이터가 여기에 들어간다. 원천 파일은 `verified_korean_horror_master.json`이다.

핵심 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `source` | 데이터 출처 |
| `source_ref_id` | 원천 JSON의 ID |
| `title` | 괴담 제목 |
| `region` | 화면 표시용 지역명 |
| `content` | 본문 |
| `metadata` | 아직 컬럼으로 고정하지 않은 원천/확장 데이터 |

`source + source_ref_id`를 유니크로 잡는 이유는 JSON import를 여러 번 실행해도 같은 데이터가 중복 저장되지 않게 하기 위해서다.

### myth_entities

신화, 전설, 괴이 존재 데이터를 저장하는 테이블이다.

원천 파일은 `ultimate_global_mythology_1000.json`이다. 괴이 이름, 기원, 행동, 약점, 생존 규칙 같은 정보를 저장한다.

핵심 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `name` | 괴이/존재 이름 |
| `origin` | 기원 또는 문화권 |
| `description` | 설명 |
| `behavior` | 행동 특성 |
| `weakness` | 약점 |
| `survival_rules` | 생존 규칙 목록 |
| `metadata` | habitats 등 가변 데이터 |

`survival_rules`는 리스트 형태일 수 있으므로 `JSONB`로 저장한다.

### superstitions

`misin.json`의 미신/금기 문장을 저장하는 테이블이다.

이 데이터는 별도 `taboos` 테이블로 가공하지 않고, 원문 문장을 단순 저장하기로 결정했다.

핵심 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `content` | 미신/금기 문장 |
| `category` | 추후 분류가 필요할 때 사용 |
| `region` | 추후 지역 표시가 필요할 때 사용 |
| `metadata` | 확장 데이터 |

### generated_stories

신규 기록실에서 사용자가 입력한 조건과 AI가 생성한 괴담 결과를 저장하는 테이블이다.

사용자가 입력하는 값:

- 지역
- 장소
- 괴이 유형
- 금기 문장
- 시간
- 발생 조건
- 결말 조건

AI가 생성한 값:

- 제목
- 본문

`status`는 초안인지 저장 완료인지 구분하고, `visibility`는 공개 여부를 구분한다.

### post_post

열린 게시판의 게시글을 저장하는 테이블이다.

현재 모델 기준으로 목격담과 창작담을 하나의 테이블에 저장하고, `category`로 구분한다.

핵심 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `author_id` | 작성자 |
| `category` | `WITNESS` 또는 `CREATION` |
| `title` | 제목 |
| `region` | 지역명 |
| `body` | 본문 |
| `views` | 조회수 |
| `likes` | 좋아요 수 캐시 |

주의할 점:

`post_like`가 실제 좋아요 기록을 저장하고, `post_post.likes`는 화면에 빠르게 보여주기 위한 숫자 캐시로 볼 수 있다. 둘을 같이 쓰면 좋아요 추가/취소 시 `Like` 테이블과 `post_post.likes` 값을 함께 맞춰야 한다.

### post_like

사용자가 게시글에 누른 좋아요 기록을 저장한다.

`post_post.likes`는 숫자만 알 수 있지만, `post_like`는 누가 어떤 글에 좋아요를 눌렀는지 알 수 있다.

제약:

```text
UNIQUE (user_id, post_id)
```

이 제약은 같은 사용자가 같은 게시글에 좋아요를 여러 번 누르지 못하게 한다.

### accounts_bookmark

PostgreSQL 내부 모델로 직접 관리하지 않는 외부 괴담 자료를 보관함에 저장하기 위한 테이블이다.

예를 들면 Neo4j 노드, 외부 원천 데이터, SCP 코드 같은 대상은 FK로 직접 연결하기 어렵다. 그래서 `horror_id`, `horror_title`, `horror_type`을 복사해서 저장한다.

장점:

- 외부 데이터도 쉽게 보관 가능
- Neo4j ID나 외부 코드만 있어도 저장 가능

주의점:

- FK가 아니므로 DB가 외부 데이터 존재 여부를 검증해주지는 않는다.
- 외부 데이터 제목이 바뀌면 보관함의 복사 제목은 자동으로 바뀌지 않는다.

### generated_story_bookmarks

AI 생성 괴담을 보관함에 저장한 기록이다.

`generated_stories`를 FK로 참조하기 때문에 원본 생성 괴담이 수정되면 보관함에서도 같은 원본을 바라본다.

제약:

```text
UNIQUE (user_id, generated_story_id)
```

같은 사용자가 같은 AI 생성 괴담을 중복 저장하지 못하게 한다.

### post_bookmarks

열린 게시판 글을 보관함에 저장한 기록이다.

`post_post`를 FK로 참조하기 때문에 게시글 제목이나 본문을 복사하지 않는다. 게시글이 수정되면 보관함에서도 수정된 게시글을 확인한다.

제약:

```text
UNIQUE (user_id, post_id)
```

같은 사용자가 같은 게시글을 중복 저장하지 못하게 한다.

## 5. 보관함이 세 종류인 이유

나의 보관함 대상은 성격이 다르다.

| 보관 대상 | 테이블 | 이유 |
| --- | --- | --- |
| 외부/Neo4j 괴담 자료 | `accounts_bookmark` | FK로 직접 연결하기 어려움 |
| AI 생성 괴담 | `generated_story_bookmarks` | `generated_stories`를 안전하게 FK 참조 가능 |
| 게시판 글 | `post_bookmarks` | `post_post`를 안전하게 FK 참조 가능 |

하나의 통합 `bookmarks` 테이블에 `target_type`, `target_id`로 저장할 수도 있지만, 그러면 DB FK 검증이 약해진다. 현재는 대상별 테이블을 나눠 안정성을 높이는 방향이다.

## 6. 제외한 테이블

| 제외 테이블 | 제외 이유 |
| --- | --- |
| `regions` | 지역 관계는 Neo4j 담당 |
| `keywords` | 현재 키워드 사용 계획 없음 |
| `story_keywords` | 키워드 테이블 제외에 따라 불필요 |
| `entity_keywords` | 키워드 테이블 제외에 따라 불필요 |
| `taboos` | `misin.json`을 구조화하지 않고 원문 저장 |
| `taboo_categories` | `taboos` 제외에 따라 불필요 |
| `daily_taboos` | 오늘의 금기 기능은 1차 DB 설계 범위 밖 |
| `comments` | 현재 게시판 댓글은 1차 범위 밖 |
| `reports` | 신고 기능은 1차 범위 밖 |

`post_like`는 팀 코드에 `Like` 모델이 들어왔기 때문에 이번 ERD 업데이트에 포함했다.

## 7. 현재 모델 기준 테이블명

이번 ERD는 현재 Django 모델과 migration 흐름을 우선한다.

`Post`, `Like`, `Bookmark` 모델에는 `Meta.db_table`이 없으므로 Django 기본 테이블명을 그대로 ERD에 반영한다.

| 모델 | ERD 테이블명 | 설명 |
| --- | --- | --- |
| `Post` | `post_post` | 열린 게시판 게시글 |
| `Like` | `post_like` | 게시글 좋아요 기록 |
| `Bookmark` | `accounts_bookmark` | 외부/Neo4j 괴담 자료 보관 기록 |

이 방식은 테이블명이 조금 덜 직관적일 수 있지만, 현재 작성된 모델과 migration을 덜 흔들고 Django 기본 규칙을 따른다는 장점이 있다.

## 8. 다음 작업

1. `database/PostgreSQL` 폴더의 SQL, query, seed 문서를 현재 ERD 테이블명과 맞춘다.
2. 모델과 ERD가 맞는지 확인한 뒤 `makemigrations`를 실행한다.
3. `migrate` 후 PostgreSQL에서 실제 테이블 목록을 확인한다.
4. JSON import 스크립트가 현재 데이터 경로와 모델 구조에 맞는지 확인한다.
