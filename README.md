# [괴이바]

> SK Networks Family AI Camp 27기 4차 프로젝트  
> 개발 기간: [2026-06-09 ~ 2026-06-10]

## Contents

1. [프로젝트 소개](#1-프로젝트-소개)
2. [팀 소개](#2-팀-소개)
3. [기술 스택](#3-기술-스택)
4. [시스템 아키텍처](#4-시스템-아키텍처)
5. [웹페이지 구현](#5-웹페이지-구현)
6. [데이터베이스 설계](#6-데이터베이스-설계)
7. [GraphDB 설계](#7-graphdb-설계)
8. [AI 괴담 생성 시나리오](#8-ai-괴담-생성-시나리오)
9. [기록 열람실 (챗봇) 구현 구조](#9-기록-열람실-챗봇-구현-구조)
10. [로그인 / 회원가입 및 보안](#10-로그인--회원가입-및-보안)
11. [테스트 및 평가](#11-테스트-및-평가)
12. [시연 화면](#12-시연-화면)
13. [기대 효과 및 결론](#13-기대-효과-및-결론)
14. [팀원 회고](#14-팀원-회고)

---

## 1. 프로젝트 소개

### 프로젝트명

**괴담 웹 서비스(괴이바)**

### 프로젝트 개요

Django 기반의 괴담 및 금기 아카이브 플랫폼으로, 다중 데이터베이스와 AI 기술을 결합하여 몰입감 있는 사용자 경험을 제공합니다. 사용자 정보 및 게시글 등 서비스 핵심 데이터는 PostgreSQL로 안정적으로 관리하며, 지역별 장소와 괴담 사이의 관계 정보는 Neo4j를 활용해 구조적으로 탐색할 수 있도록 구현했습니다. 또한 LLM을 연동하여 사용자가 직접 키워드를 입력해 새로운 괴담을 창작하고 공유할 수 있는 기능도 지원합니다.

### 개발 배경

[개발 배경 입력]

본 프로젝트는 다음 문제를 해결하기 위해 설계했습니다.

| 문제 | 해결 방향 |
|---|---|
| 파편화된 지역 괴담/금기 정보 탐색의 어려움 | PostgreSQL 기반 데이터베이스 구축 및 통합 아카이브 제공 |
| 괴담, 장소, 괴이의 복잡한 관계성 파악 한계 | Neo4j GraphDB 기반 지역-장소-괴담 관계 시각화 및 탐색 |
| 괴담 창작의 어려움 | LLM 기반 AI 괴담 생성기 및 RAGAS 평가 연동 |
| 몰입감 있는 콘텐츠 소비를 위한 분위기 부족 | 터미널형 인터페이스 및 글리치 효과, 음향 효과를 통한 독창적 UI/UX 적용 |

### 프로젝트 목표

- Django를 이용한 사용자 인증, 마이페이지, 오픈 게시판 등 웹 코어 기능 구현
- View와 Service 계층 분리를 통한 유지보수성 및 확장성 높은 시스템 구조 설계
- PostgreSQL을 활용한 금기 및 괴담 데이터 저장 및 비동기(fetch) 기반 검색 기능 제공
- Neo4j GraphDB를 활용한 지역 지도 기반 정보실 구축
- LLM 모듈 연동으로 신규 기록(AI 괴담) 자동 생성 파이프라인 구성

---

## 2. 팀 소개

### 팀명

**[괴이바]**
<table align="center" width="100%">
  <tr>
    <td align="center"><img src="docs/img/minkyungimg.png" width="110" /></td>
    <td align="center"><img src="docs/img/hwanseongimg.png" width="110" /></td>
    <td align="center"><img src="docs/img/hansolimg.png" width="110" /></td>
    <td align="center"><img src="docs/img/songwonimg.png" width="110" /></td>
    <td align="center"><img src="docs/img/jaegangimg.png" width="110" /></td>
  </tr>
  <tr>
    <td align="center"><b>김민경</b></td>
    <td align="center"><b>권환성</b></td>
    <td align="center"><b>김한솔</b></td>
    <td align="center"><b>박송원</b></td>
    <td align="center"><b>이재강</b></td>
  </tr>
  <tr>
    <td align="center">팀장</td>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
    <td align="center">팀원</td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/m2k-dcyh13">m2k-dcyh13</a></td>
    <td align="center"><a href="https://github.com/nanseong">nanseong</a></td>
    <td align="center"><a href="https://github.com/kimhansol777">kimhansol777</a></td>
    <td align="center"><a href="https://github.com/enooola0204-spec">Songwonapark87</a></td>
    <td align="center"><a href="https://github.com/leejaegang27">leejaegang27</a></td>
  </tr>
</table>

| 팀원 | 담당 업무 (WBS 기준) |
|---|---|
| **김민경** | 기획서/요구사항 정의서 작성, 폴더/프로젝트 구조 설계, `archive` 앱 구현(`TTS`, 괴담 챗봇, 자료실), 최종 코드 통합 |
| **권환성** | 프로젝트 화면 UI 설계, `accounts` 앱 구현(로그인, 회원가입, 로그아웃 Session, 마이페이지, 회원탈퇴), `archive`앱 금기자료실 구현 |
| **김한솔** | 데이터셋 수집 및 전처리, GraphDB 설계, Neo4j 적재, 벡터 임베딩, `regions` 앱 구현 |
| **박송원** | 괴담 데이터셋 확보, LLM Prompt 작성 및 연동, `generator` 앱 구현(AI 신규 기록 창작) |
| **이재강** | 데이터 전처리, PostgreSQL 기반 ERD 설계 및 pgvector 임베딩, `post` 앱 구현(열린 게시판 작성/수정/삭제) |

---

## 3. 기술 스택

### 💻 Language
<p>
  <img src="https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript" />
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" />
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3" />
</p>

### ⚙️ Framework & Database
<p>
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j" />
</p>

### 🚀 AI & Infra
<p>
  <img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge" alt="Groq" />
  <img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
</p>

### 🎨 UI/UX
- **Django Templates**: 서버 사이드 렌더링을 통한 뷰 구성
- **JavaScript (Flicker 효과)**: 무작위 화면 글리치 및 오디오 효과 연출로 오컬트 몰입감 극대화

---

## 4. 시스템 아키텍처

### 프로젝트 구조

```text
SKN27-4th-1team/
├─ config/              # Django 프로젝트 핵심 설정 및 URLConf
├─ common/              # 여러 app에서 공유하는 LLM 및 Logging 모듈
├─ accounts/            # 회원가입, 로그인, 로그아웃, 마이페이지 처리 앱
├─ archive/             # 메인페이지, 괴담 검색, 금기 조회 처리 앱
├─ generator/           # AI 괴담 생성 폼 및 RAG/LLM 연동 앱
├─ post/                # 열린 게시판 (목록, 상세, 등록, 수정, 삭제) 앱
├─ regions/             # 지역 정보실 (Neo4j 연동 지역 괴담 조회) 앱
├─ static/              # 전체 공통 정적 파일 (css, js, images, audio, fonts)
├─ templates/           # 앱별 화면 템플릿 (index, chatbot, archive, community 등)
├─ database/            # 초기 데이터 스크립트 등
└─ docker-compose.yaml  # 로컬 DB(PostgreSQL, Neo4j) 컨테이너 설정
```

### 아키텍처 특징 (View-Service 분리)
- **View (`views.py`)**: 사용자 요청 수신, 폼 검증, 권한 확인, 렌더링/리다이렉트 등 HTTP 흐름만 제어합니다.
- **Service (`services.py`)**: 실제 비즈니스 로직(DB 쿼리, 모델 저장/수정/삭제, LLM API 호출, Neo4j 연동 등)은 각 앱의 `services.py`로 분리하여 앱 간 결합도를 낮추고 재사용성을 높였습니다.

---

## 5. 웹페이지 구현

Django Template 기반으로 화면을 구성했습니다.  
각 페이지는 `templates/` 폴더에 배치하고, 공통 스타일과 인터랙션은 `static/css/styles.css`, `static/js/flicker.js`에서 관리합니다.  
HTML 파일을 직접 여는 방식이 아니라 Django URLConf와 View를 통해 페이지를 렌더링합니다.

### 화면 연결 구조

```text
Browser 요청
        ↓
config/urls.py
        ↓
각 app/urls.py
        ↓
각 app/views.py
        ↓
templates/*.html 렌더링
        ↓
static/css, static/js, images 적용
        ↓
사용자 화면 출력

```
### 주요 페이지 및 UI 구현 특징

#### 메인 페이지
<div align="center">
  <img src="docs/img/index.png" width="760" />
</div>

- URL: /
- Template: templates/archive/index.html
- 서비스 진입 화면
- 로그인 상태에 따라 LOGIN / LOGOUT 표시 변경

#### 기록 열람실
<div align="center">
  <img src="docs/img/chatbot.png" width="760" />
</div>

- URL: /archive/chatbot/
- Template: templates/archive/chatbot.html
- 괴담/기록 검색 화면
- 터미널 로그 형태의 대화형 UI 적용
- 사용자가 입력한 키워드를 기반으로 기록 검색 흐름 구성

#### 금기 자료실
<div align="center">
  <img src="docs/img/archive.png" width="760" />
</div>

- URL: /archive/archive/
- Template: templates/archive/archive.html
- superstitions DB 목록 조회
- 오늘의 금기 조회 기능

#### 신규 기록실
<div align="center">
  <img src="docs/img/stroymaker.png" width="760" />
</div>

- URL: /generator/storymaker/
- Template: templates/generator/storymaker.html
- 괴담 생성을 위한 입력 폼 제공
- 게시 성공 시 열린 게시판 창작담 탭으로 이동

#### 열린 게시판
<div align="center">
  <img src="docs/img/community.png" width="760" />
</div>

- URL: /post/community/
- Template: templates/post/community.html
- 게시글 목록, 작성, 상세 조회 기능 제공
- 본인 글일 경우 수정/삭제 버튼 표시

#### 지역 정보실
<div align="center">
  <img src="docs/img/region.png" width="760" />
</div>

- URL: /regions/regioninfo/
- Template: templates/regions/regioninfo.html
- 지역 지도 기반 정보 화면
- 지도 이미지와 확대/축소/초기화 UI 구성
- 지역 기반 괴담/장소/관계 탐색 화면으로 사용

#### 로그인
<div align="center">
  <img src="docs/img/login.png" width="760" />
</div>

- URL: /accounts/login/
- Template: templates/accounts/login.html
- 로그인 Form 제공
- 인증 실패 메시지 표시
- 로그인 처리 중 문구 출력

#### 나의 보관함
<div align="center">
  <img src="docs/img/mypage.png" width="760" />
</div>

- URL: /accounts/mypage/
- Template: templates/accounts/mypage.html
- 사용자 기본 정보 표시
- 내가 쓴 글과 보관 기록 표시
- 본인이 작성한 글 수정/삭제 가능
- 회원 탈퇴 버튼과 확인창 구현

### Static 파일 구성

static/css/styles.css
- 전체 페이지 공통 스타일
- BBS/터미널형 UI
- 로그인/회원가입 화면 스타일
- 게시판, 마이페이지, 금기 자료실, 신규 기록실 레이아웃
- 내부 스크롤 영역 제어

static/js/flicker.js
- 화면 글리치 효과
- 랜덤 간격으로 page-flicker 클래스 적용
- 괴이 이미지 랜덤 위치 노출

static/images/
- 메인 배경 이미지
- 지도 이미지
- 글리치 효과 이미지

static/audio/
- 문 열림/닫힘 효과음
- 공포 루프 사운드
- 글리치 효과음

static/fonts/
- DungGeunMo.ttf 픽셀 폰트

---

## 6. 데이터베이스 설계 (PostgreSQL)

서비스 데이터의 안정적인 저장과 조회를 위해 PostgreSQL을 주 데이터베이스로 사용합니다.

### 주요 데이터 역할
| 구분 | 내용 |
|---|---|
| 사용자 데이터 | Django 기본 Auth 모델을 확장하여 회원 계정 및 인증 세션 관리 (`accounts` 앱) |
| 커뮤니티 데이터 | 사용자가 직접 작성한 게시글 및 작성자-게시글 연결 정보 (`post` 앱) |
| 생성 결과 | AI 괴담 생성기를 통해 만들어진 결과물 및 이력 저장 (`generator` 앱) |
| 금기 데이터 | 지역 및 주제에 종속되지 않은 고유 미신/금기 데이터를 별도 관리 (`archive` 앱) |

---

## 7. GraphDB 설계 (Neo4j)

관계형 조회가 유리한 지역, 괴담, 신화 존재 간의 상호 관계를 구조적으로 탐색하기 위해 Neo4j를 분리 구성했습니다.

### 활용 목적

단순 텍스트 검색을 넘어 특정 국가/지역에 얽힌 괴담과 신화 존재를 의미 기반으로 연결하고, 이를 지도 UI와 연동하여 시각적으로 탐색할 수 있는 "지역 정보실" 기능에 활용됩니다.

### 주요 노드

| 노드 | 설명 |
|---|---|
| `Story` | DC인사이드 공포 목격담, 한국 괴담 |
| `Legend` | 세계 신화/요괴 설명 |
| `Origin` | 국가/지역 (한국, 일본, 인도 등) |
| `Region` | 한국 세부 지역 (서울, 부산 등) |
| `Place` | 구체적 장소 |
| `Location` | 장소 유형 (학교, 병원 등) |

### 주요 관계 구조

- `(Story / Legend)-[:ORIGINATED_IN]->(Origin)`
- `(Region)-[:HAS_PLACE]->(Place)`
- `(Place)-[:OCCURRED_AT]->(Story)`
- `(Story)-[:HAPPENED_IN]->(Location)`
- `(Story)-[:POSTED_ON]->(Source)`
- `(Legend)-[:WARDED_OFF_BY]->(Countermeasure)`

### 지역 정보실 조회 흐름

지도에서 국가 핀 클릭 → `Origin` 노드 기준으로 `ORIGINATED_IN` 관계를 역방향 탐색 → 해당 국가에 연결된 `Story` / `Legend` 목록 반환

---

## 8. AI 괴담 생성 시나리오

1. **사용자 요청**: `generator/storymaker/` 페이지에서 새로운 괴담 생성을 위한 키워드 입력 후 요청
2. **View-Service 라우팅**: `generator.views`가 요청을 받아 `generator.services.generate_story` 호출
3. **LLM 호출**: Service 내부에서 `common.llm_factory`를 이용해 모델 연결 후 프롬프트 기반 괴담 생성
4. **결과 평가 (선택적)**: RAGAS를 활용하여 생성된 이야기의 일관성/연관성 등을 평가
5. **저장 및 응답**: 생성 결과(`save_generated_story`)를 DB에 저장한 뒤, 화면에 결과를 반환하거나 열린 게시판으로 사용자를 유도

---

## 9. 기록 열람실 (챗봇) 구현 구조

기록 열람실 챗봇은 단순한 키워드 검색을 넘어, 사용자의 의도를 분석하고 생성형 AI를 활용하여 몰입감 있는 대화형 검색을 제공합니다.

### 전체 대화 흐름
1. **의도 분류**: 사용자의 입력을 받아 `괴담 조회`, `일반 대화`, `낭독(TTS) 요청` 세 가지 의도 중 하나로 분류합니다.
2. **DB 검색 및 선택**: `괴담 조회` 의도로 판별 시, PostgreSQL DB(`HorrorStory`, `MythEntity`, `Superstition`)에서 관련 기록을 검색하고 LLM을 통해 스산한 선택 유도문을 생성하여 반환합니다.
3. **괴담 재구성 및 평가**: 사용자가 목록에서 기록을 선택하면, 원본 기록을 바탕으로 LLM 파이프라인(생성 → 평가 → 1회 수정)을 거쳐 괴담을 재구성합니다. 평가는 키워드, 일관성, 문체, 분위기를 기준으로 진행됩니다.
4. **TTS (음성 낭독) 연동**: 재구성 완료된 괴담 텍스트는 세션에 저장되며, 사용자가 `읽어줘` 등의 명령을 내리면 ElevenLabs 스트리밍 API를 통해 낭독 오디오를 출력합니다. 동시에 YouTube IFrame API를 활용해 공포스러운 루프 사운드(BGM)를 재생하여 몰입감을 극대화합니다.
5. **세션 기반 상태 관리**: `session_state.py`를 통해 로그인 사용자와 익명 사용자의 대화 기록(History)과 마지막 생성 텍스트 상태를 분리하여 세션에 안전하게 관리합니다.

---

## 10. 로그인 / 회원가입 및 보안

Django 기본 Session 인증 방식을 사용합니다.  
HTML 템플릿 기반 구조에 맞춰 DRF Token 방식 대신 Django Session으로 로그인 상태를 관리합니다.  
`request.user`, `@login_required`, CSRF Token을 사용해 인증이 필요한 페이지와 요청을 보호합니다.

### 인증 흐름

```text
> 회원가입 인증흐름

회원가입 Form POST
        ↓
SignupForm 검증
        ↓
User 생성
        ↓
authenticate / login
        ↓
Django Session 저장
        ↓
로그인 상태 유지
```

```text
> 로그인 인증흐름

로그인 Form POST
        ↓
LoginForm 검증
        ↓
authenticate
        ↓
login(request, user)
        ↓
Django Session 저장
        ↓
로그인 상태 유지
```

### 구현 기능

회원가입
- 아이디 중복 검사
- 비밀번호 8자 이상 검사
- 비밀번호 확인 일치 검사
- 회원가입 성공 시 자동 로그인
- next 파라미터가 있으면 안전한 URL 검증 후 이동

로그인
- 아이디 / 비밀번호 기반 인증
- 로그인 성공 시 Session 생성
- 로그인 실패 시 에러 메시지 출력
- next 파라미터 지원
- 비로그인 사용자가 보호 페이지 접근 시 로그인 페이지로 이동

로그아웃
- 현재 Session 삭제
- 메인 페이지로 리다이렉트

마이페이지 보호
- @login_required 사용
- 비로그인 접근 시 /accounts/login/?next=/accounts/mypage/ 이동
- 로그인 후 원래 목적지로 복귀

---

## 11. 테스트 및 평가

| 항목 | 검증 내용 |
|---|---|
| 인증 및 세션 | 회원가입 성공 시 자동 로그인 연계 동작 검증, 세션 만료 및 로그아웃 동작 검증 |
| Service 함수화 | View에서 직접 DB 쿼리를 수행하지 않고, 순수 비즈니스 로직(Service)의 리턴값을 받아오는지 확인 |
| API 및 비동기 | 금기 자료실의 `fetch` 기반 API 통신(`archive/api/taboos/`) 및 검색 정상 동작 확인 |
| 동적 UI 테스트 | `flicker.js` 등 공포 연출 UI 스크립트 충돌 방지 및 오디오 리소스 정상 재생 검증 |

---

## 12. 시연 화면

*(프로젝트 완성 후 스크린샷 이미지 또는 GIF 파일을 이곳에 추가해 주세요)*

- **메인 페이지** (`/`)
- **기록 열람실 - 챗봇/터미널 뷰** (`/archive/chatbot/`)
- **금기 자료실** (`/archive/archive/`)
- **신규 기록실 (AI 생성 폼)** (`/generator/storymaker/`)
- **열린 게시판** (`/post/community/`)
- **지역 정보실 맵 뷰** (`/regions/regioninfo/`)

---

## 13. 기대 효과 및 결론

### 기대 효과
- **데이터 기반 아카이빙**: 파편화된 지역 괴담과 금기 지식을 효율적으로 탐색할 수 있습니다.
- **창작 활성화**: 단순 게시판을 넘어 LLM 기반 스토리 생성 기능을 제공하여 유저의 참여도와 콘텐츠 생산력을 극대화합니다.
- **몰입감 강화**: 웹 기술(JS 글리치, 픽셀 폰트, 오디오 루프 등)을 적절히 혼합하여 기존 서비스들과 차별화된 오싹한 분위기와 재미를 선사합니다.

### 결론
본 프로젝트는 Django의 풀스택 웹 개발 프레임워크 구조 위에 RDB(PostgreSQL)와 GraphDB(Neo4j)를 하이브리드 형식으로 적용했습니다. 각 데이터 특성에 맞는 DB 구성과 AI 기술의 연계로, 사용자 친화적이고 독창적인 웹서비스 아키텍처를 성공적으로 구현했습니다.

---

## 14. 팀원 회고

### [김민경]
- [회고 내용 작성]

### [권환성]
- [회고 내용 작성]

### [김한솔]
- [회고 내용 작성]

### [박송원]
- [회고 내용 작성]

### [이재강]
- [회고 내용 작성]