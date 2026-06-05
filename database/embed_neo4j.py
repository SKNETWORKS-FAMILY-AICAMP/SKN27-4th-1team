import os
import time
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase


def get_driver():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'neo4j_password')
    return GraphDatabase.driver(uri, auth=(user, password))


def run_embedding():
    print("Connecting to Neo4j database...")
    driver = get_driver()

    print("Loading local sentence-transformers model (paraphrase-multilingual-MiniLM-L12-v2)...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    targets = [
        {"label": "Story", "text_prop": "body"},
        {"label": "Legend", "text_prop": "name"},
        {"label": "SCP", "text_prop": "text"},
    ]

    with driver.session() as session:
        print("Creating Neo4j Vector Indexes...")
        session.run("""
        CREATE VECTOR INDEX story_embeddings IF NOT EXISTS
        FOR (s:Story) ON (s.embedding)
        OPTIONS {indexConfig: {
          `vector.dimensions`: 384,
          `vector.similarity_function`: 'cosine'
        }}
        """)
        session.run("""
        CREATE VECTOR INDEX legend_embeddings IF NOT EXISTS
        FOR (l:Legend) ON (l.embedding)
        OPTIONS {indexConfig: {
          `vector.dimensions`: 384,
          `vector.similarity_function`: 'cosine'
        }}
        """)
        session.run("""
        CREATE VECTOR INDEX scp_embeddings IF NOT EXISTS
        FOR (s:SCP) ON (s.embedding)
        OPTIONS {indexConfig: {
          `vector.dimensions`: 384,
          `vector.similarity_function`: 'cosine'
        }}
        """)

        time.sleep(2)

        for target in targets:
            label = target["label"]
            text_prop = target["text_prop"]

            print(f"\nProcessing embeddings for label: {label} ...")
            result = session.run(f"MATCH (n:{label}) RETURN n.id AS id, n.{text_prop} AS text")
            nodes = [{"id": r["id"], "text": r["text"] or ""} for r in result]

            total = len(nodes)
            print(f"Found {total} nodes of label {label} to embed.")

            batch_size = 100
            for i in range(0, total, batch_size):
                batch = nodes[i:i + batch_size]
                texts = [node["text"][:1000] for node in batch]
                vectors = model.encode(texts).tolist()

                batch_data = [{"id": node["id"], "vector": vector} for node, vector in zip(batch, vectors)]

                query = f"""
                UNWIND $batch AS row
                MATCH (n:{label} {{id: row.id}})
                SET n.embedding = row.vector
                """
                session.run(query, batch=batch_data)
                print(f"-> Embedded {min(i + batch_size, total)}/{total} nodes of label {label}")

    driver.close()
    print("\n--- Neo4j Local Vector Indexing Completed Successfully! ---")


if __name__ == '__main__':
    run_embedding()
