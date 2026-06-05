import os
import sys
import io
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_driver():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'neo4j_password')
    return GraphDatabase.driver(uri, auth=(user, password))


def main():
    driver = get_driver()
    with driver.session() as session:
        print("--- Story Verification ---")
        for r in session.run("""
        MATCH (s:Story)
        WHERE s.name CONTAINS '마스크' OR s.id STARTS WITH 'story_yokai' OR s.id STARTS WITH 'story_legend'
        RETURN s.id AS id, s.name AS name, size(s.body) AS body_len, size(s.embedding) AS emb_dim
        LIMIT 5
        """):
            print(f"ID: {r['id']}, Name: {r['name']}, Body Length: {r['body_len']}, Embedding Dimension: {r['emb_dim']}")

        print("\n--- Legend Verification ---")
        for r in session.run("""
        MATCH (l:Legend) WHERE l.body IS NOT NULL
        RETURN l.id AS id, l.name AS name, size(l.body) AS body_len, size(l.embedding) AS emb_dim
        LIMIT 5
        """):
            print(f"ID: {r['id']}, Name: {r['name']}, Body Length: {r['body_len']}, Embedding Dimension: {r['emb_dim']}")

        print("\n--- SCP Verification ---")
        for r in session.run("""
        MATCH (s:SCP) WHERE s.text IS NOT NULL
        RETURN s.id AS id, s.name AS name, size(s.text) AS body_len, size(s.embedding) AS emb_dim
        LIMIT 5
        """):
            print(f"ID: {r['id']}, Name: {r['name']}, Body Length: {r['body_len']}, Embedding Dimension: {r['emb_dim']}")

        print("\n--- Region/Place Verification ---")
        for r in session.run("""
        MATCH (reg:Region)-[:HAS_PLACE]->(p:Place)
        RETURN reg.name AS region, count(p) AS place_count
        LIMIT 10
        """):
            print(f"Region: {r['region']}, Places: {r['place_count']}")

    driver.close()


if __name__ == '__main__':
    main()
