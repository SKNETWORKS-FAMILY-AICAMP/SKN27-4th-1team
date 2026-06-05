# PostgreSQL ERD 설명

## 1. 문서 목적

이 문서는 `postgresql_erd_plan.md`에서 설계한 PostgreSQL ERD를 실제 구현자가 이해하기 쉽게 풀어쓴 설명 문서이다.

ERD 그림은 테이블과 관계를 한눈에 보여주지만, 각 테이블에 어떤 데이터가 들어가는지, 왜 필요한지, 어떤 JSON 파일과 연결되는지는 별도로 설명이 필요하다. 이 문서는 그 부분을 정리한다.

## 2. 전체 구조 요약

PostgreSQL은 서비스 화면에서 직접 저장하고 조회해야 하는 데이터를 담당한다.

```text
회원
괴담 원천 데이터
신화/괴이 존재 데이터
미신 문장 데이터
AI 생성 괴담
게시판 글
나의 보관함
```

반대로 지역 간 관계, 괴이와 장소의 연결, 그래프 탐색은 Neo4j가 담당한다. 그래서 PostgreSQL에는 `regions` 테이블을 만들지 않고, 필요한 경우 `region` 문자열 컬럼만 둔다.

## 3. 테이블 목록

| 테이블 | 역할 |
| --- | --- |
| `auth_user` | Django 기본 사용자 테이블 |
| `horror_stories` | 한국 괴담/도시전설 원천 데이터 저장 |
| `myth_entities` | 신화/전설/괴이 존재 데이터 저장 |
| `superstitions` | 미신/금기 문장 원문 저장 |
| `generated_stories` | 사용자가 입력 조건으로 생성한 AI 괴담 저장 |
| `posts` | 열린 게시판의 목격담/창작담 게시글 저장 |
| `generated_story_bookmarks` | 사용자가 저장한 AI 생성 괴담 목록 |
| `post_bookmarks` | 사용자가 저장한 게시글 목록 |

## 4. 테이블별 설명

### auth_user

`auth_user`는 Django가 기본으로 제공하는 사용자 테이블이다.

로그인, 회원가입, 작성자 정보, 보관함 소유자 정보를 처리할 때 사용한다. 별도의 `users` 테이블을 새로 만들지 않고 Django 기본 인증 테이블을 그대로 사용한다.

주요 사용 위치:

```text
로그인
회원가입
신규 기록실 작성자
열린 게시판 작성자
나의 보관함 소유자
```

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | 사용자 고유 ID |
| `username` | 로그인 ID |
| `email` | 이메일 |

## 5. archive 영역

archive 영역은 기록 열람실, 금기 자료실처럼 원천 데이터를 조회하는 화면과 관련 있다.

### horror_stories

`horror_stories`는 한국 괴담/도시전설 원천 데이터를 저장하는 테이블이다.

대상 JSON:

```text
docs/verified_korean_horror_master.json
```

예시 데이터:

```text
장산범
빨간 마스크
구미호
도깨비
```

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | DB 내부 고유 ID |
| `source` | 데이터 출처. 예: `namu_wiki` |
| `source_ref_id` | 원본 JSON의 `id` |
| `title` | 괴담 제목 |
| `language` | 언어. 기본값은 `ko` |
| `region` | 화면 표시용 지역명 |
| `url` | 원문 URL |
| `preview` | 목록에서 보여줄 짧은 미리보기 |
| `content` | 전체 본문 |
| `category` | 도시전설, 괴담 등 분류 |
| `metadata` | 지금 당장 컬럼화하지 않을 원본/확장 데이터 |

구현 주의:

```text
source + source_ref_id 조합은 UNIQUE로 둔다.
url은 중복 가능성을 고려해 unique로 묶지 않는다.
preview는 원본에 없으므로 import 시 content 앞부분으로 생성할 수 있다.
```

### myth_entities

`myth_entities`는 신화, 전설, 괴이 존재 정보를 저장하는 테이블이다.

대상 JSON:

```text
docs/ultimate_global_mythology_1000.json
```

예시 데이터:

```text
호문클루스
요괴
저지 데블
구미호
도깨비
```

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | DB 내부 고유 ID |
| `source` | 데이터셋 출처. 기본값은 `ultimate_global_mythology_1000` |
| `source_ref_id` | 원본 JSON의 `id` |
| `name` | 괴이 존재 이름 |
| `origin` | 기원 또는 문화권 |
| `description` | 전체 설명 |
| `behavior` | 행동 특징 |
| `weakness` | 약점 |
| `history` | 역사/전승 |
| `signs` | 출현 징후 |
| `survival_rules` | 생존 규칙 목록 |
| `source_site` | 출처 사이트 |
| `source_url` | 출처 URL |
| `metadata` | `habitats` 등 가변 데이터 |

구현 주의:

```text
source + source_ref_id 조합은 UNIQUE로 둔다.
habitats는 리스트 형태이므로 metadata에 넣는다.
survival_rules는 JSONB로 저장한다.
```

### superstitions

`superstitions`는 미신/금기 문장을 원문 그대로 저장하는 테이블이다.

대상 JSON:

```text
docs/misin.json
```

예시 데이터:

```text
밤에 깎아서 버린 손톱을 쥐가 주워 먹으면...
머릿수로 사람을 세면 귀신 머리까지 함께 세게 된다.
귀신 이야기를 한 후에는 어깨를 털어야 한다.
```

중요한 결정:

```text
misin.json은 taboos 테이블로 가공하지 않는다.
문장 그대로 superstitions에 저장한다.
```

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | DB 내부 고유 ID |
| `source` | 데이터셋 출처. 기본값은 `misin` |
| `source_ref_id` | 원본 JSON의 `id` |
| `content` | 미신/금기 문장 원문 |
| `category` | 추후 분류가 필요할 때 사용 |
| `region` | 추후 지역 표시가 필요할 때 사용 |
| `metadata` | 추후 확장 데이터 |

구현 주의:

```text
source + source_ref_id 조합은 UNIQUE로 둔다.
content는 중복 문장이 있을 수 있으므로 unique로 묶지 않는다.
```

## 6. generator 영역

### generated_stories

`generated_stories`는 사용자가 신규 기록실에서 입력한 조건과 AI가 생성한 괴담 결과를 저장하는 테이블이다.

화면 기준:

```text
신규 기록실
나의 보관함 중 창작담 기록
```

사용자가 입력할 수 있는 값:

```text
지역
장소
괴이 유형
금기 문장
시간
발생 조건
결말
```

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | 생성 괴담 고유 ID |
| `user_id` | 작성자. `auth_user.id` 참조 |
| `region` | 사용자가 입력한 지역 |
| `place` | 장소 |
| `entity_type` | 귀신, 요괴, 저주 등 |
| `taboo_text` | 사용자가 입력한 금기 문장 |
| `event_time` | 발생 시간 |
| `condition` | 발생 조건 |
| `ending` | 결말 조건 |
| `title` | AI가 만든 제목 |
| `content` | AI가 만든 본문 |
| `status` | draft, saved 등 상태 |
| `visibility` | private, public 등 공개 여부 |
| `prompt_payload` | AI 호출에 사용한 입력 조건 원본 |

구현 주의:

```text
taboo_text는 FK가 아니다.
taboos 테이블을 만들지 않기 때문에 단순 텍스트로 저장한다.
prompt_payload는 나중에 AI 프롬프트 재현이나 디버깅에 쓸 수 있다.
```

## 7. post 영역

### posts

`posts`는 열린 게시판의 글을 저장하는 테이블이다.

화면 기준:

```text
열린 게시판
목격담 탭
창작담 탭
```

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | 게시글 고유 ID |
| `user_id` | 작성자. `auth_user.id` 참조 |
| `board_type` | 게시판 종류. 예: `witness`, `creation` |
| `title` | 게시글 제목 |
| `region` | 사용자가 입력한 지역 |
| `content` | 게시글 본문 |
| `view_count` | 조회수 |
| `visibility` | 공개 여부 |
| `created_at` | 작성일 |
| `updated_at` | 수정일 |

구현 주의:

```text
댓글, 추천, 신고는 MVP에서 제외한다.
따라서 comments, likes, reports 테이블은 1차 ERD에 만들지 않는다.
```

## 8. accounts 보관함 영역

나의 보관함은 하나의 통합 `bookmarks` 테이블이 아니라 대상별 테이블로 나눈다.

이유:

```text
DB 레벨 FK를 명확하게 걸 수 있다.
generated_stories와 posts를 각각 안전하게 참조할 수 있다.
구현자가 target_type, target_id를 직접 해석하지 않아도 된다.
```

### generated_story_bookmarks

`generated_story_bookmarks`는 사용자가 AI 생성 괴담을 저장했을 때 사용하는 테이블이다.

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | 보관 기록 ID |
| `user_id` | 저장한 사용자 |
| `generated_story_id` | 저장한 AI 생성 괴담 |
| `memo` | 사용자 메모 |
| `created_at` | 저장일 |

제약 조건:

```text
UNIQUE (user_id, generated_story_id)
```

같은 사용자가 같은 생성 괴담을 여러 번 저장하지 못하게 한다.

### post_bookmarks

`post_bookmarks`는 사용자가 열린 게시판 글을 저장했을 때 사용하는 테이블이다.

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | 보관 기록 ID |
| `user_id` | 저장한 사용자 |
| `post_id` | 저장한 게시글 |
| `memo` | 사용자 메모 |
| `created_at` | 저장일 |

제약 조건:

```text
UNIQUE (user_id, post_id)
```

같은 사용자가 같은 게시글을 여러 번 저장하지 못하게 한다.

## 9. 테이블 관계 설명

### auth_user와 generated_stories

```text
auth_user 1 : N generated_stories
```

한 명의 사용자는 여러 개의 AI 생성 괴담을 만들 수 있다.

### auth_user와 posts

```text
auth_user 1 : N posts
```

한 명의 사용자는 여러 개의 게시글을 작성할 수 있다.

### auth_user와 bookmarks

```text
auth_user 1 : N generated_story_bookmarks
auth_user 1 : N post_bookmarks
```

한 명의 사용자는 여러 개의 생성 괴담과 게시글을 보관할 수 있다.

### generated_stories와 generated_story_bookmarks

```text
generated_stories 1 : N generated_story_bookmarks
```

하나의 생성 괴담은 여러 사용자에게 저장될 수 있다.

### posts와 post_bookmarks

```text
posts 1 : N post_bookmarks
```

하나의 게시글은 여러 사용자에게 저장될 수 있다.

## 10. 제외한 테이블

1차 PostgreSQL ERD에서는 다음 테이블을 만들지 않는다.

| 제외 대상 | 제외 이유 |
| --- | --- |
| `regions` | 지역 관계는 Neo4j가 담당 |
| `keywords` | 원본 JSON에 키워드 컬럼이 없고 현재 사용 계획 없음 |
| `story_keywords` | 키워드 테이블 제외에 따라 불필요 |
| `entity_keywords` | 키워드 테이블 제외에 따라 불필요 |
| `taboos` | `misin.json`을 구조화하지 않고 원문 저장하기로 결정 |
| `taboo_categories` | `taboos` 제외에 따라 불필요 |
| `daily_taboos` | 오늘의 금기 기능은 1차 구현 대상 아님 |
| `comments` | 댓글은 MVP 제외 |
| `likes` | 추천은 MVP 제외 |
| `reports` | 신고는 MVP 제외 |

## 11. JSON 파일과 테이블 매핑

| JSON 파일 | 적재 테이블 | 적재 방식 |
| --- | --- | --- |
| `docs/verified_korean_horror_master.json` | `horror_stories` | 괴담 원천 데이터로 저장 |
| `docs/ultimate_global_mythology_1000.json` | `myth_entities` | 괴이 존재 데이터로 저장 |
| `docs/misin.json` | `superstitions` | 문장 원문 그대로 저장 |

`global_horror_database.json`은 사용하지 않기로 했으므로 1차 ERD 적재 대상에서 제외한다.

## 12. 구현할 때 기억할 점

```text
1. Django 기본 auth_user를 사용한다.
2. 별도 users 테이블은 만들지 않는다.
3. 각 모델에는 Meta.db_table을 명시한다.
4. 원천 데이터 테이블은 source + source_ref_id로 중복 적재를 막는다.
5. region은 FK가 아니라 문자열 컬럼이다.
6. taboo_text는 FK가 아니라 텍스트 입력값이다.
7. JSONB 컬럼은 원본 보존과 확장용이다.
```

## 13. 다음 작업

이 설명을 기준으로 다음 순서로 구현하면 된다.

```text
1. Django models.py 작성
2. makemigrations 실행
3. migrate 실행
4. docs JSON seed/import 스크립트 작성
5. 데이터 적재 후 개수 확인
6. ERDCloud 그림과 실제 DB 테이블 비교
```
