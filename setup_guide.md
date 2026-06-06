# Setup Guide

## Python

- Python 3.12

## Django App 구조

확정 app은 아래 5개로 나눕니다.

- `accounts`: 회원가입, 로그인, 로그아웃, 사용자 인증, 마이페이지 기본 정보
- `archive`: 괴담/금기 아카이브, 괴담 검색, 금기 조회, 오늘의 금기 조회
- `generator`: AI 괴담 생성, RAG/LLM 연동, 생성 결과 저장, RAGAS 기반 평가
- `post`: 목격담 게시판 작성, 목록, 상세, 수정, 삭제
- `regions`: 지역 지도, Neo4j 기반 지역 괴담 조회

## 폴더 구조

```text
SKN27-4th-1team/
|-- manage.py
|-- requirements.txt
|-- README.md
|-- docker-compose.yaml       # PostgreSQL, Neo4j 등 로컬 개발용 컨테이너 설정
|
|-- config/                  # Django 프로젝트 설정
|   |-- settings.py
|   |-- urls.py
|   |-- wsgi.py
|   `-- asgi.py
|
|-- common/                  # 여러 app에서 함께 쓰는 공통 코드
|   |-- llm_factory.py       # LLM 객체 생성
|   `-- logging.py           # 공통 로깅 helper
|
|-- templates/               # 전체 템플릿
|   |-- base.html            # 모든 페이지가 상속하는 공통 레이아웃
|   |
|   |-- accounts/            # 로그인, 회원가입, 나의 기록
|   |   |-- login.html
|   |   |-- signup.html
|   |   `-- mypage.html
|   |
|   |-- archive/             # 메인, 기록 열람실, 금기 자료실
|   |   |-- index.html
|   |   |-- chatbot.html
|   |   `-- archive.html
|   |
|   |-- generator/           # 신규 기록실
|   |   `-- storymaker.html
|   |
|   |-- post/                # 열린 게시판
|   |   `-- community.html
|   |
|   `-- regions/             # 지역 정보실
|       `-- regioninfo.html
|
|-- static/                  # 전체 공통 정적 파일
|   |-- css/
|   |   `-- styles.css
|   |-- js/
|   |   `-- flicker.js
|   |-- images/
|   |   |-- dark-room.png
|   |   |-- goei_map_thin_red.png
|   |   |-- jumpscare.avif
|   |   |-- jumpscare.jpeg
|   |   `-- red-room.png
|   |-- fonts/
|   |   `-- DungGeunMo.ttf
|   `-- audio/
|       |-- closedoor.mp3
|       |-- horror-loop.wav
|       |-- jumpscare-sting.wav
|       |-- opendoor.mp3
|       `-- switch-sound.m4a
|
|-- accounts/                # 회원가입, 로그인, 로그아웃, 마이페이지 기본 정보
|   |-- admin.py
|   |-- apps.py
|   |-- forms.py             # 로그인/회원가입 form
|   |-- models.py            # 사용자 관련 확장 모델
|   |-- services.py          # 인증/사용자 관련 비즈니스 로직
|   |-- tests.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|       `-- __init__.py
|
|-- archive/                 # 괴담/금기 아카이브, 오늘의 금기
|   |-- admin.py
|   |-- apps.py
|   |-- models.py            # 괴담/금기 데이터 모델
|   |-- services.py          # 괴담/금기 검색, 오늘의 금기 랜덤 조회
|   |-- tests.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|       `-- __init__.py
|
|-- generator/               # AI 괴담 생성 + evaluation
|   |-- admin.py
|   |-- apps.py
|   |-- models.py            # 생성 결과 저장 모델
|   |-- services.py          # LLM 호출
|   |-- tests.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|       `-- __init__.py
|
|-- post/                    # 목격기록 게시판 CRUD
|   |-- admin.py
|   |-- apps.py
|   |-- forms.py             # 목격기록 작성/수정 form
|   |-- models.py            # 목격기록 게시글 모델
|   |-- services.py          # 게시글 작성/조회/수정/삭제 로직
|   |-- tests.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|       `-- __init__.py
|
|-- regions/                 # 지역도감, Neo4j 기반 지역 괴담 조회
|   |-- admin.py
|   |-- apps.py
|   |-- models.py            # 필요 시 지역 캐시/조회 기록 모델
|   |-- services.py          # Neo4j 연결, 지역-장소-괴담 관계 조회
|   |-- tests.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|       `-- __init__.py
|
`-- docs/
    |-- requirements-definition.csv
    |-- wbs.csv
    `-- service-planning.md
```

## service 위치 규칙

- app 내부 로직은 각 app의 `services.py`에 둡니다.
- 코드가 커지면 `services/` 폴더로 분리할 수 있습니다.
- 여러 app에서 공통으로 쓰는 LLM, logging 같은 기능만 `common/`에 둡니다.
- view에는 요청/응답 처리만 두고, 실제 처리 로직은 service로 분리합니다.

예시:

```text
generator/services.py
- 괴담 생성 요청 구성
- RAG 검색 결과 조합
- LLM 응답 후처리
- RAGAS 평가 실행
- evaluation 결과 저장 또는 로그 기록

regions/services.py
- Neo4j 연결
- 지역 기반 괴담 조회 쿼리

archive/services.py
- 금기 랜덤 조회
- 괴담/금기 검색
```

## 팀 공통 개발 규칙

### urls.py 규칙

- `urls.py`에는 URL path만 작성합니다.
- DB 조회, form 처리, LLM 호출, Neo4j 쿼리 같은 로직은 작성하지 않습니다.
- URL name은 기능별로 아래 이름을 우선 사용합니다.

```text
index
list
detail
create
update
delete
login
logout
signup
generate
```

예시:

```python
path("", views.index, name="index")
path("create/", views.create, name="create")
path("<int:pk>/", views.detail, name="detail")
```

### views.py 규칙

- `views.py`는 요청과 응답 흐름만 담당합니다.
- GET/POST 분기, form 검증, 로그인 여부 확인, service 호출, `render`/`redirect`/`JsonResponse` 반환만 작성합니다.
- 복잡한 DB 조회, 저장/수정/삭제 로직, LLM 호출, Neo4j 쿼리는 직접 작성하지 않습니다.
- 필요한 처리는 각 앱의 `services.py` 함수로 분리합니다.

예시 흐름:

```text
request
-> form 검증
-> services.py 함수 호출
-> render 또는 redirect 반환
```

### services.py 규칙

- `services.py`에는 실제 비즈니스 로직을 작성합니다.
- DB 조회/저장/수정/삭제, LLM 호출, Neo4j 조회, 데이터 가공 로직을 담당합니다.
- `request`, `render`, `redirect`는 사용하지 않습니다.
- Django response 객체를 반환하지 않고, model 객체, QuerySet, list, dict, bool 등을 반환합니다.

예시:

```python
def get_today_taboo():
    return taboo
```

```python
def list_user_posts(user):
    return posts
```

### 앱 간 데이터 호출 규칙

- 다른 앱의 데이터가 필요하면 해당 앱의 model을 직접 import하기보다 해당 앱의 `services.py` 함수를 우선 호출합니다.
- 단, 모델 관계 설정이나 migration 작성처럼 model import가 필요한 경우는 예외로 합니다.

예시:

```text
accounts에서 내가 쓴 목격담 조회
-> post.services.list_user_posts(user)

accounts에서 내가 생성한 괴담 조회
-> generator.services.list_user_generated_stories(user)

generator에서 지역 정보 참고
-> regions.services.get_region_detail(region_name)
```

### 앱별 대표 service 함수

각 담당자는 아래 함수 형태를 기준으로 구현을 시작합니다.

```text
accounts.services
- signup_user(data)
- login_user(request, user_id, password)
- logout_user(request)
- get_user_profile(user)

post.services
- list_posts()
- get_post(post_id)
- create_post(user, data)
- update_post(post, data)
- delete_post(post)
- list_user_posts(user)

archive.services
- list_stories()
- search_stories(keyword)
- list_taboos()
- get_today_taboo()
- get_taboo(taboo_id)

generator.services
- generate_story(input_data, user=None)
- save_generated_story(user, data)
- list_user_generated_stories(user)

regions.services
- get_region_list()
- get_region_detail(region_name)
- get_region_places(region_name)
```

### MVP 범위에서 제외하는 것

- RAG, Graph RAG, embedding, pgvector는 MVP에서 제외합니다.
- Neo4j는 RAG가 아니라 지역/장소/괴이/금기 관계 조회 용도로만 사용합니다.
- 저장된 괴담을 참고한 생성은 후순위 기능으로 둡니다.

## 데이터 역할 분리

- PostgreSQL: 사용자, 게시글, 저장 기록, 생성 결과
- Neo4j: 지역, 장소, 괴담, 괴이 사이의 관계 조회
- 금기 데이터: 지역/주제 메타데이터 없이 `archive`에서 독립 콘텐츠로 관리


## 역할 분담 초안

5명 기준으로 기술별 담당보다 Django app과 화면 단위로 나눕니다. 각 페이지의 HTML, CSS, JavaScript는 이미 완성되어 있으므로, 각 담당자는 맡은 app에서 기존 화면 파일을 Django template/static 구조로 연결하고 데이터 흐름을 구현합니다.

1. accounts app: 회원가입, 로그인, 로그아웃, 사용자 인증, 마이페이지 기본 정보
2. archive app: 괴담/금기 아카이브, 괴담 검색, 금기 조회, 오늘의 금기 조회, 상세 조회, 저장한 괴담 조회
3. generator app: AI 괴담 생성, 생성 결과 저장, evaluation
4. post app: 목격담 게시판 작성, 목록, 상세, 수정, 삭제
5. regions app: 지역 지도, Neo4j 기반 지역 괴담 조회, 지역-장소-괴담 관계 탐색

- PostgreSQL은 사용자, 게시글, 저장 기록 같은 서비스 데이터를 담당합니다.
- Neo4j는 지역, 장소, 괴담, 괴이 사이의 관계 탐색을 담당합니다.

공통 담당 규칙:

- 완성된 HTML, CSS, JavaScript의 공통 레이아웃과 리소스 경로를 Django 구조에 맞게 정리합니다.
- 금기는 지역/주제 메타데이터 없이 archive app에서 독립 콘텐츠로 관리합니다.
