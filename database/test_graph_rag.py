from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

def test_query(query_text):
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "rulemate1234"
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    print(f"\n[USER QUERY]: {query_text}")
    print("Loading embedding model...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    # 1. Generate query embedding vector
    query_vector = model.encode(query_text).tolist()
    
    with driver.session() as session:
        # A. Search Story Vector Index
        print("\n--- 1. Vector Search inside 'Story' nodes ---")
        story_query = """
        CALL db.index.vector.queryNodes('story_embeddings', 2, $vector)
        YIELD node AS story, score
        OPTIONAL MATCH (story)-[:HAPPENED_IN]->(l:Location)
        OPTIONAL MATCH (story)-[:FEATURES]->(leg:Legend)
        RETURN story.name AS title, 
               substring(story.body, 0, 150) AS preview, 
               collect(DISTINCT l.name) AS locations,
               collect(DISTINCT leg.name) AS legends,
               score
        """
        results = session.run(story_query, vector=query_vector)
        for r in results:
            print(f"Title: {r['title']}")
            print(f"Score: {r['score']:.4f}")
            print(f"Keywords/Legends detected: {r['legends']}")
            print(f"Locations detected: {r['locations']}")
            print(f"Body Preview: {r['preview']}...\n")

        # B. Search SCP Vector Index (Testing multilingual mapping)
        print("\n--- 2. Vector Search inside 'SCP' nodes (Cross-language Test) ---")
        scp_query = """
        CALL db.index.vector.queryNodes('scp_embeddings', 2, $vector)
        YIELD node AS scp, score
        OPTIONAL MATCH (scp)-[:LIVES_IN]->(t:Location)
        OPTIONAL MATCH (scp)-[:WARDED_OFF_BY]->(c:Countermeasure)
        RETURN scp.name AS code_title,
               substring(scp.text, 0, 150) AS preview,
               collect(DISTINCT t.name) AS tags,
               collect(DISTINCT c.name) AS object_classes,
               score
        """
        results_scp = session.run(scp_query, vector=query_vector)
        for r in results_scp:
            print(f"SCP: {r['code_title']}")
            print(f"Score: {r['score']:.4f}")
            print(f"Object Class: {r['object_classes']}")
            print(f"Tags/Attributes: {r['tags']}")
            print(f"Text Preview: {r['preview']}...\n")

    driver.close()

if __name__ == '__main__':
    # Test query
    test_query("학교 화장실에서 빨간 휴지나 파란 휴지를 물어보는 귀신 이야기")
