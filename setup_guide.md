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
|   |-- prompt.py            # 공통 프롬프트
|   |-- logging.py           # 공통 로깅 helper
|   `-- responses.py         # JsonResponse 응답 helper
|
|-- templates/               # 전체 템플릿
|   |-- base.html            # 모든 페이지가 상속하는 공통 레이아웃
|   |
|   |-- accounts/            # 로그인, 회원가입, 나의 기록
|   |   |-- login.html
|   |   |-- signup.html
|   |   `-- mygirok.html
|   |
|   |-- archive/             # 메인, 실록관, 금기록
|   |   |-- index.html
|   |   |-- sillokgwan.html
|   |   `-- geumgirok.html
|   |
|   |-- generator/           # 괴이제조소
|   |   `-- goeijejoso.html
|   |
|   |-- post/                # 목격기록
|   |   `-- mokgyeokgirok.html
|   |
|   `-- regions/             # 지역도감
|       `-- jidogam.html
|
|-- static/                  # 전체 공통 정적 파일
|   |-- css/
|   |   `-- styles.css
|   |-- js/
|   |   `-- flicker.js
|   |-- images/
|   |-- fonts/
|   `-- audio/
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
|-- generator/               # AI 괴담 생성, RAG, RAGAS/evaluation
|   |-- admin.py
|   |-- apps.py
|   |-- models.py            # 생성 결과 저장 모델
|   |-- services.py          # LLM 호출, RAG 조합, RAGAS 평가
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
    |-- wbs.csv
    `-- service-planning.md
```

## service 위치 규칙

- app 내부 로직은 각 app의 `services.py`에 둡니다.
- 코드가 커지면 `services/` 폴더로 분리할 수 있습니다.
- 여러 app에서 공통으로 쓰는 LLM, prompt, logging 같은 기능만 `common/`에 둡니다.
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

## 데이터 역할 분리

- PostgreSQL: 사용자, 게시글, 저장 기록, 생성 결과
- Neo4j: 지역, 장소, 괴담, 괴이 사이의 관계 조회
- 금기 데이터: 지역/주제 메타데이터 없이 `archive`에서 독립 콘텐츠로 관리


## 역할 분담 초안

5명 기준으로 기술별 담당보다 Django app과 화면 단위로 나눕니다. 각 페이지의 HTML, CSS, JavaScript는 이미 완성되어 있으므로, 각 담당자는 맡은 app에서 기존 화면 파일을 Django template/static 구조로 연결하고 데이터 흐름을 구현합니다.

1. accounts app: 회원가입, 로그인, 로그아웃, 사용자 인증, 마이페이지 기본 정보
2. archive app: 괴담/금기 아카이브, 괴담 검색, 금기 조회, 오늘의 금기 조회, 상세 조회, 저장한 괴담 조회
3. generator app: AI 괴담 생성, RAG/LLM 연동, 생성 결과 저장, RAGAS/evaluation
4. post app: 목격담 게시판 작성, 목록, 상세, 수정, 삭제
5. regions app: 지역 지도, Neo4j 기반 지역 괴담 조회, 지역-장소-괴담 관계 탐색

공통 담당 규칙:

- 완성된 HTML, CSS, JavaScript의 공통 레이아웃과 리소스 경로를 Django 구조에 맞게 정리합니다.
- PostgreSQL은 사용자, 게시글, 저장 기록 같은 서비스 데이터를 담당합니다.
- Neo4j는 지역, 장소, 괴담, 괴이 사이의 관계 탐색을 담당합니다.
- 금기는 지역/주제 메타데이터 없이 archive app에서 독립 콘텐츠로 관리합니다.
- RAG/LLM 로직과 RAGAS/evaluation은 generator app을 중심으로 만들고, 필요한 app에서 호출합니다.
