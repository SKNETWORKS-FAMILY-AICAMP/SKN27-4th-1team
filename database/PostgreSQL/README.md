# PostgreSQL 작업 정리

## 목적

이 폴더는 괴이 실록 서비스의 PostgreSQL 관련 산출물을 모아두는 공간이다.

ERD 설계 문서는 `database/ERD/`에 두고, PostgreSQL 구현과 확인에 필요한 스키마 SQL, 데이터 적재 계획, 검증 쿼리는 이 폴더에서 관리한다.

## 폴더 구조

```text
database/PostgreSQL/
├─ README.md
├─ schema.sql
├─ seed_plan.md
├─ import_json_data.py
└─ queries/
   ├─ count_check.sql
   └─ sample_select.sql
```

## 파일 역할

| 파일 | 역할 |
| --- | --- |
| `schema.sql` | ERDCloud import, 제출, DB 구조 참고용 CREATE TABLE SQL |
| `seed_plan.md` | docs JSON 파일을 어떤 테이블에 적재할지 정리 |
| `import_json_data.py` | Django ORM으로 docs JSON 파일을 PostgreSQL에 적재 |
| `queries/count_check.sql` | 데이터 적재 후 테이블별 개수 확인 |
| `queries/sample_select.sql` | 화면 조회를 가정한 샘플 SELECT |

## Django와의 관계

Django 프로젝트에서는 실제 테이블 생성은 보통 `models.py`와 migration이 담당한다.

따라서 이 폴더의 `schema.sql`은 직접 실행용이라기보다 다음 용도에 가깝다.

```text
ERDCloud import용
설계 검토용
제출/발표 참고용
Django models.py 작성 기준
```

실제 구현 흐름은 다음과 같다.

```text
1. database/ERD 문서 확인
2. database/PostgreSQL/schema.sql 확인
3. Django models.py 작성
4. python manage.py makemigrations
5. python manage.py migrate
6. JSON seed/import 스크립트 작성
7. 적재 후 queries/count_check.sql 기준으로 개수 확인
```

## 데이터 적재 명령

PostgreSQL 컨테이너가 실행 중이고 migration이 완료된 뒤 프로젝트 루트에서 실행한다.

```bash
python database/PostgreSQL/import_json_data.py
```

## 1차 PostgreSQL 테이블

```text
auth_user
horror_stories
myth_entities
superstitions
generated_stories
posts
generated_story_bookmarks
post_bookmarks
```

## 제외 대상

아래 항목은 1차 PostgreSQL ERD에서 제외한다.

```text
regions
keywords
story_keywords
entity_keywords
taboos
taboo_categories
daily_taboos
comments
likes
reports
```

지역 관계와 그래프 탐색은 Neo4j가 담당한다.
