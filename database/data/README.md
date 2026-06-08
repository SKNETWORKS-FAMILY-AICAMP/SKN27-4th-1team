# 데이터 파이프라인 가이드

팀원이 처음 세팅할 때 순서대로 따라하면 됩니다.

---

## 데이터 구성

| 파일 | 설명 | 건수 |
|---|---|---|
| `verified_korean_horror_master.json` | 나무위키 한국 괴담/도시전설 | 325건 |
| `ultimate_global_mythology_1000.json` | 나무위키 전세계 요괴/신화 (게임/무기 항목 제거) | 604건 |
| `dcinside_horror_filtered.json` | DC인사이드 공포갤 크롤링 (전처리 완료) | 2,204건 |
| `preprocessed_scp.json` | ko.scp-wiki.net 한국어 크롤링 | 2,198건 |
| `misin.json` | 한국 미신/금기 | 214건 |

> `nodes.csv`, `edges.csv`는 gitignore 처리되어 있으므로 아래 3단계에서 직접 생성합니다.

---

## 실행 순서

### 전제 조건

```bash
# 가상환경 활성화
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Mac/Linux

# Docker 컨테이너 실행
docker-compose up -d
```

---

### 1단계 — PostgreSQL 세팅

```bash
# 마이그레이션 생성 및 적용
python manage.py makemigrations
python manage.py migrate

# 데이터 import (HorrorStory 325건 + MythEntity 700건 + SCP 2198건 + Superstition 214건)
python database/PostgreSQL/import_json_data.py
```

---

### 2단계 — Neo4j 그래프 데이터 생성

```bash
# nodes.csv, edges.csv 생성 (database/data/ 에 저장됨)
python src/embedding/extract_all_graph_data.py
```

---

### 3단계 — Neo4j import

```bash
# Neo4j에 노드/엣지 적재 + 본문 바인딩
python src/embedding/import_to_neo4j.py
```

---

### 4단계 — 벡터 임베딩

```bash
# Story / Legend / SCP 노드 임베딩 생성
python src/embedding/embed_neo4j.py
```

> 임베딩 모델: `paraphrase-multilingual-MiniLM-L12-v2` (자동 다운로드)

---

### 5단계 — 서버 실행

```bash
python manage.py runserver
```

---


## 전체 초기화 (DB 날리고 다시 시작)

```bash
docker-compose down -v
docker-compose up -d
python manage.py makemigrations
python manage.py migrate
python database/PostgreSQL/import_json_data.py
python src/embedding/extract_all_graph_data.py
python src/embedding/import_to_neo4j.py
python src/embedding/embed_neo4j.py
```

---

## 환경변수 (.env)

```
POSTGRES_DB=goei_sillok
POSTGRES_USER=postgres
POSTGRES_PASSWORD=post1234
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_password
NEO4J_AUTH=neo4j/neo4j_password
```
