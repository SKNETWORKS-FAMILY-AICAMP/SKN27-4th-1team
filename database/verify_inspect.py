import sys
import io
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "rulemate1234"))
    with driver.session() as session:
        # Check story with '마스크' or similar Korean characters
        res = session.run("""
        MATCH (s:Story) 
        WHERE s.name CONTAINS '마스크' OR s.id STARTS WITH 'story_yokai' OR s.id STARTS WITH 'story_legend'
        RETURN s.id AS id, s.name AS name, size(s.body) AS body_len, size(s.embedding) AS emb_dim 
        LIMIT 5
        """)
        print("--- Story Verification ---")
        for r in res:
            print(f"ID: {r['id']}, Name: {r['name']}, Body Length: {r['body_len']}, Embedding Dimension: {r['emb_dim']}")

        # Check Legend count and details
        res_legend = session.run("""
        MATCH (l:Legend) 
        WHERE l.body IS NOT NULL
        RETURN l.id AS id, l.name AS name, size(l.body) AS body_len, size(l.embedding) AS emb_dim 
        LIMIT 5
        """)
        print("\n--- Legend Verification ---")
        for r in res_legend:
            print(f"ID: {r['id']}, Name: {r['name']}, Body Length: {r['body_len']}, Embedding Dimension: {r['emb_dim']}")

        # Check SCP count and details
        res_scp = session.run("""
        MATCH (s:SCP) 
        WHERE s.text IS NOT NULL
        RETURN s.id AS id, s.name AS name, size(s.text) AS body_len, size(s.embedding) AS emb_dim 
        LIMIT 5
        """)
        print("\n--- SCP Verification ---")
        for r in res_scp:
            print(f"ID: {r['id']}, Name: {r['name']}, Body Length: {r['body_len']}, Embedding Dimension: {r['emb_dim']}")

    driver.close()

if __name__ == '__main__':
    main()
