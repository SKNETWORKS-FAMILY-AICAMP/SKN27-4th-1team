import os
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase


def get_driver():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'neo4j_password')
    return GraphDatabase.driver(uri, auth=(user, password))


def test_query(query_text):
    driver = get_driver()
    print(f"\n[USER QUERY]: {query_text}")
    print("Loading embedding model...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    query_vector = model.encode(query_text).tolist()

    with driver.session() as session:
        print("\n--- 1. Vector Search inside 'Story' nodes ---")
        results = session.run("""
        CALL db.index.vector.queryNodes('story_embeddings', 2, $vector)
        YIELD node AS story, score
        OPTIONAL MATCH (story)-[:HAPPENED_IN]->(l:Location)
        OPTIONAL MATCH (story)-[:FEATURES]->(leg:Legend)
        RETURN story.name AS title,
               substring(story.body, 0, 150) AS preview,
               collect(DISTINCT l.name) AS locations,
               collect(DISTINCT leg.name) AS legends,
               score
        """, vector=query_vector)
        for r in results:
            print(f"Title: {r['title']}")
            print(f"Score: {r['score']:.4f}")
            print(f"Legends: {r['legends']}")
            print(f"Locations: {r['locations']}")
            print(f"Preview: {r['preview']}...\n")

        print("\n--- 2. Vector Search inside 'SCP' nodes ---")
        results_scp = session.run("""
        CALL db.index.vector.queryNodes('scp_embeddings', 2, $vector)
        YIELD node AS scp, score
        OPTIONAL MATCH (scp)-[:LIVES_IN]->(t:Location)
        OPTIONAL MATCH (scp)-[:WARDED_OFF_BY]->(c:Countermeasure)
        RETURN scp.name AS code_title,
               substring(scp.text, 0, 150) AS preview,
               collect(DISTINCT t.name) AS tags,
               collect(DISTINCT c.name) AS object_classes,
               score
        """, vector=query_vector)
        for r in results_scp:
            print(f"SCP: {r['code_title']}")
            print(f"Score: {r['score']:.4f}")
            print(f"Object Class: {r['object_classes']}")
            print(f"Tags: {r['tags']}")
            print(f"Preview: {r['preview']}...\n")

    driver.close()


if __name__ == '__main__':
    test_query("학교 화장실에서 빨간 휴지나 파란 휴지를 물어보는 귀신 이야기")
