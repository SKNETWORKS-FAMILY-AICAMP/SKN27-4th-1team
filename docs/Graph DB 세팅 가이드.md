# Graph DB 세팅 가이드

Neo4j 데이터 로드 및 벡터 임베딩을 처음 세팅할 때 이 순서대로 실행하면 됩니다.

## 전제 조건

### 1. .env 확인

프로젝트 루트의 `.env` 파일에 아래 값이 있어야 합니다.

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_password
NEO4J_AUTH=neo4j/neo4j_password
```

`.env.example`을 참고해서 만들어주세요.

### 2. Neo4j 실행

```bash
docker compose up -d
```

Neo4j가 `bolt://localhost:7687`에서 실행됩니다.  
브라우저에서 `http://localhost:7474` 로 접속해서 확인할 수 있어요.

---

## 실행 순서

프로젝트 루트에서 실행하세요.

### Step 1. nodes.csv / edges.csv 생성

```bash
python src/embedding/extract_all_graph_data.py
```

- `database/data/` 폴더의 JSON 파일들을 읽어 `database/data/nodes.csv`, `database/data/edges.csv` 를 생성합니다.
- 이미 파일이 있으면 덮어씁니다.

### Step 2. Neo4j에 데이터 로드

```bash
python src/embedding/import_to_neo4j.py
```

- 기존 Neo4j 데이터를 전부 삭제하고 새로 로드합니다.
- 노드 유형: `Story`, `Legend`, `Yokai`, `SCP`, `Location`, `Countermeasure`, `Source`, `Origin`, `Region`, `Place`
- `Region → Place → Story` 관계도 이 단계에서 생성됩니다 (한국 공포 데이터 기반).
- 각 노드에 본문(`body` / `text`) 속성을 JSON 파일에서 바인딩합니다.

> Neo4j 컨테이너가 시작 직후라면 연결 대기를 자동으로 재시도합니다 (최대 30초).

### Step 3. 벡터 임베딩 생성

```bash
python src/embedding/embed_neo4j.py
```

- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` 모델을 로컬에서 실행합니다.
- `Story`, `Legend`, `SCP` 노드에 384차원 임베딩 벡터를 추가합니다.
- 처음 실행 시 모델 다운로드가 필요합니다 (약 500MB).
- 노드 수에 따라 수 분이 소요됩니다.

### Step 4. 검증

```bash
python src/embedding/verify_inspect.py
```

- 각 노드 유형의 본문 길이, 임베딩 차원, Region/Place 연결 수를 출력합니다.
- 임베딩 차원이 `384`로 출력되면 정상입니다.

---

## 문제가 생기면

### Neo4j 연결 실패

`.env`의 `NEO4J_PASSWORD` 값과 `NEO4J_AUTH` 값의 비밀번호 부분이 일치하는지 확인하세요.

```
NEO4J_PASSWORD=neo4j_password
NEO4J_AUTH=neo4j/neo4j_password  ← 여기 비밀번호와 같아야 함
```

### LOAD CSV 오류

`import_to_neo4j.py` 실행 시 `LOAD CSV` 오류가 나면 `nodes.csv`, `edges.csv`를 Neo4j import 폴더로 복사해야 합니다.

```bash
# Docker 컨테이너로 복사
docker cp database/data/nodes.csv goei_neo4j:/var/lib/neo4j/import/nodes.csv
docker cp database/data/edges.csv goei_neo4j:/var/lib/neo4j/import/edges.csv
```

그 다음 Step 2를 다시 실행하세요.

### 임베딩 모델 다운로드 실패

인터넷 연결 확인 후 아래 명령으로 직접 다운로드하세요.

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

---

## 벡터 검색 테스트

세팅 완료 후 검색이 잘 되는지 테스트할 수 있습니다.

```bash
python src/embedding/test_graph_rag.py
```
