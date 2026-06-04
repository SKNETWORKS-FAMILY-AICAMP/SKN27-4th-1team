import time
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

def run_embedding():
    # 1. Connect to Neo4j
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "rulemate1234"
    
    print("Connecting to Neo4j database...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # 2. Load Local Embedding Model (Free & Offline)
    print("Loading local sentence-transformers model (paraphrase-multilingual-MiniLM-L12-v2)...")
    # This is a high-performance multilingual model mapping Ko/En text to 384-dimensional vector space
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    
    # 3. Target nodes to embed
    targets = [
        {"label": "Story", "text_prop": "body"},
        {"label": "Legend", "text_prop": "name"}, # Using name for Legend as detailed description is short/unstructured
        {"label": "SCP", "text_prop": "text"}
    ]
    
    with driver.session() as session:
        # Create Vector Indexes inside Neo4j first
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
        
        # Give Neo4j a small window to initialize indexes
        time.sleep(2)
        
        for target in targets:
            label = target["label"]
            text_prop = target["text_prop"]
            
            print(f"\nProcessing embeddings for label: {label} ...")
            # Fetch target nodes
            result = session.run(f"MATCH (n:{label}) RETURN n.id AS id, n.{text_prop} AS text")
            nodes = [{"id": r["id"], "text": r["text"] or ""} for r in result]
            
            total = len(nodes)
            print(f"Found {total} nodes of label {label} to embed.")
            
            # Batch size for bulk updates
            batch_size = 100
            for i in range(0, total, batch_size):
                batch = nodes[i:i+batch_size]
                
                # Compute embeddings locally
                texts = [node["text"][:1000] for node in batch] # Cap at 1000 chars to speed up
                vectors = model.encode(texts).tolist()
                
                # Prepare batch update mapping
                batch_data = []
                for node, vector in zip(batch, vectors):
                    batch_data.append({
                        "id": node["id"],
                        "vector": vector
                    })
                    
                # Run Bulk Update UNWIND Query
                query = f"""
                UNWIND $batch AS row
                MATCH (n:{label} {{id: row.id}})
                SET n.embedding = row.vector
                """
                session.run(query, batch=batch_data)
                print(f"-> Embedded {min(i+batch_size, total)}/{total} nodes of label {label}")
                
    driver.close()
    print("\n--- Neo4j Local Vector Indexing Completed Successfully! (0 USD Cost) ---")

if __name__ == '__main__':
    run_embedding()
