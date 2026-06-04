import time
from neo4j import GraphDatabase
import sys
import io

# Force terminal and file systems to interpret using UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_import():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "rulemate1234"
    
    print("Connecting to Neo4j database...")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # Wait for the DB to be ready and responsive
    retries = 10
    connected = False
    for i in range(retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
                connected = True
                print("Neo4j database is ready.")
                break
        except Exception:
            print(f"Waiting for Neo4j... ({i+1}/{retries})")
            time.sleep(3)
            
    if not connected:
        print("Error: Could not connect to Neo4j. Make sure the Docker container is running.")
        driver.close()
        return

    with driver.session() as session:
        # 1. Clean existing database
        print("Cleaning existing database...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # 2. Drop existing indexes if any, then create constraints
        print("Creating constraints and indexes...")
        try:
            session.run("CREATE CONSTRAINT UNIQUE_NODE_ID FOR (n:Yokai) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_LEGEND_ID FOR (n:Legend) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_STORY_ID FOR (n:Story) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_LOC_ID FOR (n:Location) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_COUNTER_ID FOR (n:Countermeasure) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_SRC_ID FOR (n:Source) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_ORIGIN_ID FOR (n:Origin) REQUIRE n.id IS UNIQUE")
        except Exception: pass
        try:
            session.run("CREATE CONSTRAINT UNIQUE_SCP_ID FOR (n:SCP) REQUIRE n.id IS UNIQUE")
        except Exception: pass

        # 3. Load Nodes from nodes.csv by Labels
        print("Importing Nodes from nodes.csv...")
        # Since CSV contains label column, we iterate through labels to dynamically create them with proper types
        labels = ["Yokai", "Legend", "Story", "Location", "Countermeasure", "Source", "Origin", "SCP"]
        for label in labels:
            print(f"-> Creating nodes with label: {label}")
            query = f"""
            LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
            WITH row WHERE row.label = '{label}'
            CREATE (n:{label} {{id: row.id, name: row.name}})
            """
            session.run(query)
            
        # Create indexes on 'id' for fast matching
        for label in labels:
            try:
                session.run(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
            except Exception: pass
            
        # --- BIND BODY/TEXT PROPERTY FROM ORIGINAL JSON FILES ---
        print("\nBinding original content text to nodes...")
        import json
        import os
        docs_dir = 'docs'
        preprocessing_dir = 'processing'
        
        # A. Bind Korean master (both stories and legends/yokai)
        korean_path = os.path.join(docs_dir, 'verified_korean_horror_master.json')
        if os.path.exists(korean_path):
            print("-> Binding verified_korean_horror_master.json...")
            with open(korean_path, 'r', encoding='utf-8') as f:
                korean_data = json.load(f)
            import re
            def normalize_string(s):
                return re.sub(r'[^a-zA-Z0-9가-힣]', '', str(s)).lower()
            
            story_updates = []
            legend_updates = []
            
            for item in korean_data:
                title = item.get('title')
                content = item.get('content', '').strip()
                norm = normalize_string(title)
                
                if not content or not norm:
                    continue
                
                # Bind content to whatever node types exist for this entity (Story/Legend/Yokai)
                story_updates.append({"id": f"story_{norm}", "content": content})
                legend_updates.append({"id": f"legend_{norm}", "content": content})
                legend_updates.append({"id": f"yokai_{norm}", "content": content})
            
            # Update Story nodes
            session.run("""
            UNWIND $batch AS row
            MATCH (n:Story {id: row.id})
            SET n.body = CASE WHEN row.content IS NOT NULL AND row.content <> '' THEN row.content ELSE n.body END
            """, batch=story_updates)
            
            # Update Legend nodes
            session.run("""
            UNWIND $batch AS row
            MATCH (n:Legend {id: row.id})
            SET n.body = CASE WHEN row.content IS NOT NULL AND row.content <> '' THEN row.content ELSE n.body END
            """, batch=legend_updates)
            
            # Update Yokai nodes
            session.run("""
            UNWIND $batch AS row
            MATCH (n:Yokai {id: row.id})
            SET n.body = CASE WHEN row.content IS NOT NULL AND row.content <> '' THEN row.content ELSE n.body END
            """, batch=legend_updates)

        # B. Bind Global master mythology descriptions to Legend nodes
        global_path = os.path.join(docs_dir, 'ultimate_global_mythology_1000.json')
        if os.path.exists(global_path):
            print("-> Binding ultimate_global_mythology_1000.json...")
            with open(global_path, 'r', encoding='utf-8') as f:
                global_data = json.load(f)
            global_updates = []
            for item in global_data:
                name = item.get('name')
                desc = item.get('description_raw', '')
                norm = re.sub(r'[^a-zA-Z0-9가-힣]', '', str(name)).lower()
                global_updates.append({"id": f"legend_{norm}", "desc": desc})
            session.run("""
            UNWIND $batch AS row
            MATCH (l:Legend {id: row.id})
            SET l.body = CASE WHEN row.desc IS NOT NULL AND row.desc <> '' THEN row.desc ELSE l.body END
            """, batch=global_updates)

        # C. Bind Reddit stories to Story nodes
        reddit_path = os.path.join(docs_dir, 'global_horror_database.json')
        if os.path.exists(reddit_path):
            print("-> Binding global_horror_database.json (limited to 5000 updates to optimize performance)...")
            with open(reddit_path, 'r', encoding='utf-8') as f:
                reddit_data = json.load(f)
            reddit_updates = []
            for item in reddit_data[:5000]:
                title = item.get('title')
                text = item.get('full_content', item.get('text', ''))
                norm = re.sub(r'[^a-zA-Z0-9가-힣]', '', str(title)).lower()
                if norm:
                    reddit_updates.append({"id": f"story_{norm}", "body": text})
            session.run("""
            UNWIND $batch AS row
            MATCH (s:Story {id: row.id})
            SET s.body = CASE WHEN row.body IS NOT NULL AND row.body <> '' THEN row.body ELSE s.body END
            """, batch=reddit_updates)

        # D. Bind SCP texts to SCP nodes
        scp_path = os.path.join(preprocessing_dir, 'preprocessed_scp.json')
        if os.path.exists(scp_path):
            print("-> Binding preprocessed_scp.json...")
            with open(scp_path, 'r', encoding='utf-8') as f:
                scp_data = json.load(f)
            scp_updates = []
            for item in scp_data:
                code = item.get('code')
                text = item.get('text', '')
                norm = re.sub(r'[^a-zA-Z0-9가-힣]', '', str(code)).lower()
                if norm:
                    scp_updates.append({"id": f"scp_{norm}", "text": text})
            session.run("""
            UNWIND $batch AS row
            MATCH (n:SCP {id: row.id})
            SET n.text = CASE WHEN row.text IS NOT NULL AND row.text <> '' THEN row.text ELSE n.text END
            """, batch=scp_updates)

        # E. Bind Creepypasta texts to Story nodes
        cp_path = os.path.join(preprocessing_dir, 'preprocessed_creepypastas.json')
        if os.path.exists(cp_path):
            print("-> Binding preprocessed_creepypastas.json...")
            with open(cp_path, 'r', encoding='utf-8') as f:
                cp_data = json.load(f)
            cp_updates = []
            for item in cp_data:
                title = item.get('title')
                body = item.get('body', '')
                norm = re.sub(r'[^a-zA-Z0-9가-힣]', '', str(title)).lower()
                if norm:
                    cp_updates.append({"id": f"story_{norm}", "body": body})
            session.run("""
            UNWIND $batch AS row
            MATCH (s:Story {id: row.id})
            SET s.body = CASE WHEN row.body IS NOT NULL AND row.body <> '' THEN row.body ELSE s.body END
            """, batch=cp_updates)

        # 4. Load Edges from edges.csv
        print("Importing Edges (Relationships) from edges.csv...")
        # To dynamically assign relationship types in Cypher LOAD CSV without APOC, we can filter by type or use APOC.
        # Since rulemate packages include neo4j library and we have standard types, let's load edges and use Cypher dynamically or filter by known types.
        rel_types = ["RECORDED_IN", "WARDED_OFF_BY", "ORIGINATED_IN", "HAPPENED_IN", "POSTED_ON", "FEATURES", "LIVES_IN"]
        for r_type in rel_types:
            print(f"-> Linking relationships of type: {r_type}")
            query = f"""
            LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
            WITH row WHERE row.type = '{r_type}'
            MATCH (source {{id: row.source}})
            MATCH (target {{id: row.target}})
            CREATE (source)-[r:{r_type}]->(target)
            """
            session.run(query)

        # 5. Summary verification
        print("\nVerifying imported counts:")
        result = session.run("MATCH (n) RETURN labels(n) AS labels, count(n) AS cnt")
        for record in result:
            print(f"Label: {record['labels']} - Count: {record['cnt']}")
            
        result_edges = session.run("MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt")
        for record in result_edges:
            print(f"Relationship: {record['rel_type']} - Count: {record['cnt']}")

    driver.close()
    print("Graph DB Import Completed Successfully!")

if __name__ == '__main__':
    run_import()
