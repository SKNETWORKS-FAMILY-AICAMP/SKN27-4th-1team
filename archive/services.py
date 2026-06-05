"""Business logic for the archive app."""
import os
import json
import socket
import requests
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

# Lazy loading of embedding model to optimize startup time
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        # Using the same multilingual model as defined in database migration scripts
        _embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    return _embedding_model

def get_neo4j_driver():
    """Dynamically resolves host name to avoid Docker container vs localhost confusion, then returns the Neo4j driver."""
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'rulemate1234')

    try:
        host_part = uri.split("//")[1].split(":")[0]
        socket.gethostbyname(host_part)
    except Exception:
        uri = f"bolt://localhost:7687"

    return GraphDatabase.driver(uri, auth=(user, password))

def search_horror_records(query_text):
    """
    Searches the Neo4j DB for Story, Legend, or SCP using Hybrid Search (Vector similarity + text keyword).
    Returns a list of dicts.
    """
    if not query_text:
        return []

    driver = get_neo4j_driver()
    results = {}

    query_clean = query_text.strip()
    
    # Generate embedding vector for semantic search (only for queries with length >= 3)
    query_vector = None
    if len(query_clean) >= 3:
        try:
            model = get_embedding_model()
            query_vector = model.encode(query_clean).tolist()
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            query_vector = None

    # Cypher Queries
    # 1. Keyword search (Exact / CONTAINS matching fallback)
    # If query is 1 character, only match name exactly.
    # If query is 2 characters, only match name via CONTAINS.
    # If query is 3+ characters, search name, body, and text.
    if len(query_clean) < 2:
        keyword_cypher = """
        MATCH (n)
        WHERE (n:Story OR n:Legend OR n:SCP)
          AND n.name IS NOT NULL 
          AND toLower(n.name) = toLower($q)
        OPTIONAL MATCH (n)-[:HAPPENED_IN|LIVES_IN]->(l:Location)
        OPTIONAL MATCH (n)-[:OCCURRED_AT]->(p:Place)-[:HAS_PLACE]-(r:Region)
        RETURN labels(n)[0] AS type,
               n.id AS id,
               n.name AS name,
               coalesce(n.body, n.text, '') AS body,
               collect(DISTINCT coalesce(l.name, r.name, '전국')) AS regions
        LIMIT 15
        """
    elif len(query_clean) == 2:
        keyword_cypher = """
        MATCH (n)
        WHERE (n:Story OR n:Legend OR n:SCP)
          AND n.name IS NOT NULL 
          AND toLower(n.name) CONTAINS toLower($q)
        OPTIONAL MATCH (n)-[:HAPPENED_IN|LIVES_IN]->(l:Location)
        OPTIONAL MATCH (n)-[:OCCURRED_AT]->(p:Place)-[:HAS_PLACE]-(r:Region)
        RETURN labels(n)[0] AS type,
               n.id AS id,
               n.name AS name,
               coalesce(n.body, n.text, '') AS body,
               collect(DISTINCT coalesce(l.name, r.name, '전국')) AS regions
        LIMIT 15
        """
    else:
        keyword_cypher = """
        MATCH (n)
        WHERE (n:Story OR n:Legend OR n:SCP)
          AND (
            (n.name IS NOT NULL AND toLower(n.name) CONTAINS toLower($q))
            OR (n.body IS NOT NULL AND toLower(n.body) CONTAINS toLower($q))
            OR (n.text IS NOT NULL AND toLower(n.text) CONTAINS toLower($q))
          )
        OPTIONAL MATCH (n)-[:HAPPENED_IN|LIVES_IN]->(l:Location)
        OPTIONAL MATCH (n)-[:OCCURRED_AT]->(p:Place)-[:HAS_PLACE]-(r:Region)
        RETURN labels(n)[0] AS type,
               n.id AS id,
               n.name AS name,
               coalesce(n.body, n.text, '') AS body,
               collect(DISTINCT coalesce(l.name, r.name, '전국')) AS regions
        LIMIT 15
        """

    # 2. Vector Semantic Search (Only if indices exist and vector generated successfully)
    # Search Story vectors
    vector_story_cypher = """
    CALL db.index.vector.queryNodes('story_embeddings', 5, $vector)
    YIELD node AS n, score
    OPTIONAL MATCH (n)-[:HAPPENED_IN]->(l:Location)
    RETURN 'Story' AS type,
           n.id AS id,
           n.name AS name,
           coalesce(n.body, '') AS body,
           collect(DISTINCT l.name) AS regions,
           score
    """

    # Search SCP vectors
    vector_scp_cypher = """
    CALL db.index.vector.queryNodes('scp_embeddings', 5, $vector)
    YIELD node AS n, score
    OPTIONAL MATCH (n)-[:LIVES_IN]->(l:Location)
    RETURN 'SCP' AS type,
           n.id AS id,
           n.name AS name,
           coalesce(n.text, '') AS body,
           collect(DISTINCT l.name) AS regions,
           score
    """

    with driver.session() as session:
        # Run text keyword query
        try:
            keyword_records = session.run(keyword_cypher, q=query_clean)
            for r in keyword_records:
                rid = r['id']
                # If the query is directly inside the node name, give it a top priority score of 2.0
                name_match = r['name'] and query_clean.lower() in r['name'].lower()
                score = 2.0 if name_match else 1.2
                results[rid] = {
                    'type': r['type'],
                    'id': rid,
                    'name': r['name'],
                    'body': r['body'],
                    'regions': r['regions'] if r['regions'] else ['전국'],
                    'score': score
                }
        except Exception as e:
            print(f"Error querying text search from Neo4j: {e}")

        # Run Vector queries if vector is available
        if query_vector:
            try:
                story_records = session.run(vector_story_cypher, vector=query_vector)
                for r in story_records:
                    score = float(r['score'])
                    if score < 0.77:  # Skip irrelevant / generic conversational results
                        continue
                    rid = r['id']
                    if rid not in results or results[rid]['score'] < score:
                        results[rid] = {
                            'type': r['type'],
                            'id': rid,
                            'name': r['name'],
                            'body': r['body'],
                            'regions': r['regions'] if r['regions'] else ['전국'],
                            'score': score
                        }
            except Exception as ex:
                print(f"Skipping Story vector search (index might not exist): {ex}")

            try:
                scp_records = session.run(vector_scp_cypher, vector=query_vector)
                for r in scp_records:
                    score = float(r['score'])
                    if score < 0.77:  # Skip irrelevant / generic conversational results
                        continue
                    rid = r['id']
                    if rid not in results or results[rid]['score'] < score:
                        results[rid] = {
                            'type': r['type'],
                            'id': rid,
                            'name': r['name'],
                            'body': r['body'],
                            'regions': r['regions'] if r['regions'] else ['전국'],
                            'score': score
                        }
            except Exception as ex:
                print(f"Skipping SCP vector search (index might not exist): {ex}")

    driver.close()

    # Sort results by score (descending) and return as list
    sorted_results = sorted(results.values(), key=lambda x: x['score'], reverse=True)
    return sorted_results[:10]


SYSTEM_PROMPT = (
    "너는 괴이실록 시스템(BBS DOS)의 AI 안내자이다. 스산하고 기괴한 터미널 컨셉에 맞춰 행동하라.\n"
    "사용자가 입력한 검색어와 데이터베이스에서 찾은 괴담 기록(Context)이 주어집니다.\n"
    "너는 반드시 아래 형식의 JSON 객체로만 응답해야 한다:\n"
    "{\n"
    "  \"is_certain\": true 또는 false,\n"
    "  \"picked_index\": 사용자의 질문에 부합하는 가장 유사한 기록 번호 (1부터 시작하는 정수, 완전히 무관하면 null),\n"
    "  \"response\": \"사용자에게 보여줄 터미널 출력용 대화 메시지\"\n"
    "}\n\n"
    "규칙:\n"
    "1. [완전히 무관한 질문/인사말의 경우]:\n"
    "   사용자의 검색어(예: 안녕?, 날씨 등)가 검색 결과(Context)들과 완전히 뜬금없고 아무 연관도 없다면, is_certain을 false로 하고 picked_index를 반드시 null로 설정하라.\n"
    "   response에는 괴담과 무관한 인사말이나 질문이 들어왔음을 알리며, 괴담이나 기록을 입력해 달라고 스산하게 요청하라.\n"
    "2. [의도가 확실한 경우 (is_certain: true)]:\n"
    "   검색 결과 중 사용자의 검색어에 정확히 일치하거나 매우 밀접한 기록이 단 하나 존재한다면, is_certain을 true로 하고 picked_index를 1로 지정하라.\n"
    "   response에는 그 기록의 특징, 위험성, 현상 등을 3줄 내외로 오싹하게 설명하고 마지막에 '이 기록이 당신이 찾던 기록이 맞습니까?'라고 물어라.\n"
    "3. [의도가 애매하지만 유력한 후보가 있는 경우 (is_certain: false)]:\n"
    "   검색 결과(Context)가 존재하고 사용자의 질문이 괴담과 연관은 있으나 불명확하다면, is_certain을 false로 하고 picked_index를 1로 지정하라.\n"
    "   response에는 질문이 확실치 않으나 이 기록(기록 #1)이 가장 근접해 보인다고 명칭을 언급하며 특징을 요약하고, '이 기록이 당신이 찾던 기록이 맞습니까?'라고 되물어라.\n"
    "4. [기록이 전혀 없는 경우]: 검색 결과가 없다면, picked_index를 null로 하고 데이터베이스에 관련 괴이의 흔적이 없음을 오싹하게 알려라.\n"
    "5. 절대 기호('A', 'B')나 안내용 가이드를 그대로 출력하지 말고, 실제 기록 제목을 언급하라.\n"
    "6. 존댓말과 차가운 터미널 어조를 유지하며, 대답은 오직 유효한 JSON 형식이어야 한다.\n"
    "7. response는 반드시 한 문단, 한 번만 작성하라. 같은 내용을 두 번 반복하거나 줄바꿈으로 나눠 쓰지 말라."
)


def clean_and_parse_json(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def rewrite_query(query, conversation_history):
    """Uses a fast LLM to rewrite follow-up queries into proper search keywords."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or not conversation_history:
        return query

    history_text = ""
    for msg in conversation_history[-6:]:
        role = "사용자" if msg["role"] == "user" else "시스템"
        history_text += f"{role}: {msg['content']}\n"

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 한국 괴담 아카이브 검색 시스템의 쿼리 재작성기다.\n"
                    "대화 히스토리와 현재 사용자 입력을 보고, Neo4j 데이터베이스에 검색할 키워드 하나만 출력하라.\n"
                    "규칙:\n"
                    "1. '그거 말고는', '다른 거', '또 없어?', '비슷한 거', '더 없어?' 같은 후속 질문이면 "
                    "이전 대화에서 검색 주제를 추출해서 그 키워드를 그대로 반환하라.\n"
                    "2. 완전히 새로운 독립 질문이면 그 질문을 그대로 반환하라.\n"
                    "3. 검색 키워드만 출력하라. 설명, 문장, 따옴표 없이."
                )
            },
            {
                "role": "user",
                "content": f"[대화 히스토리]\n{history_text}\n[현재 입력]\n{query}"
            }
        ],
        "temperature": 0.0,
        "max_tokens": 50
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=5
        )
        if resp.status_code == 200:
            rewritten = resp.json()["choices"][0]["message"]["content"].strip()
            return rewritten if rewritten else query
    except Exception:
        pass
    return query


def call_groq_llm_structured(query, retrieved_docs, conversation_history=None):
    """Calls Groq API and returns structured JSON with is_certain, picked_index, response."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {
            "is_certain": False,
            "picked_index": None,
            "response": "[SYSTEM WARNING] GROQ_API_KEY가 등록되지 않았습니다. .env 파일에 GROQ_API_KEY=gsk_... 값을 설정해 주십시오."
        }

    context_str = ""
    for idx, doc in enumerate(retrieved_docs):
        context_str += f"[기록 #{idx+1}]\n제목: {doc['name']}\n유형: {doc['type']}\n지역: {', '.join(doc['regions'])}\n본문: {doc['body'][:300]}...\n\n"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({
        "role": "user",
        "content": f"검색어: {query}\n\n[참고 데이터베이스 기록]\n{context_str if retrieved_docs else '참고할 수 있는 기록 없음'}"
    })

    payload = {
        "model": "llama-3.3-70b-versatile",
        "response_format": {"type": "json_object"},
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            return clean_and_parse_json(resp.json()["choices"][0]["message"]["content"])
        return {"is_certain": False, "picked_index": None, "response": f"[시스템 경고] Groq API 응답 에러 (코드 {resp.status_code})"}
    except Exception as e:
        return {"is_certain": False, "picked_index": None, "response": f"[시스템 장애] LLM 서비스 연결 중 에러 발생: {str(e)}"}

