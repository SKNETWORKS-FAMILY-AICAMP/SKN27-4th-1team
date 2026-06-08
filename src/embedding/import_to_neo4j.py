import os
import sys
import io
import json
import re
import time
from neo4j import GraphDatabase

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_driver():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'neo4j_password')
    return GraphDatabase.driver(uri, auth=(user, password))


def normalize_string(s):
    return re.sub(r'[^a-zA-Z0-9가-힣]', '', str(s)).lower()


def run_import():
    print("Connecting to Neo4j database...")
    driver = get_driver()

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
            print(f"Waiting for Neo4j... ({i + 1}/{retries})")
            time.sleep(3)

    if not connected:
        print("Error: Could not connect to Neo4j.")
        driver.close()
        return

    with driver.session() as session:
        print("Cleaning existing database...")
        session.run("MATCH (n) DETACH DELETE n")

        print("Creating constraints and indexes...")
        for label, constraint in [
            ("Yokai", "UNIQUE_NODE_ID"), ("Legend", "UNIQUE_LEGEND_ID"),
            ("Story", "UNIQUE_STORY_ID"), ("Location", "UNIQUE_LOC_ID"),
            ("Countermeasure", "UNIQUE_COUNTER_ID"), ("Source", "UNIQUE_SRC_ID"),
            ("Origin", "UNIQUE_ORIGIN_ID"), ("SCP", "UNIQUE_SCP_ID"),
            ("Region", "UNIQUE_REGION_ID"), ("Place", "UNIQUE_PLACE_ID"),
        ]:
            try:
                session.run(f"CREATE CONSTRAINT {constraint} FOR (n:{label}) REQUIRE n.id IS UNIQUE")
            except Exception:
                pass

        print("Importing Nodes from nodes.csv...")
        labels = ["Yokai", "Legend", "Story", "Location", "Countermeasure", "Source", "Origin", "SCP"]
        for label in labels:
            print(f"-> Creating nodes with label: {label}")
            session.run(f"""
            LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
            WITH row WHERE row.label = '{label}'
            CREATE (n:{label} {{id: row.id, name: row.name}})
            """)

        for label in labels + ["Region", "Place"]:
            try:
                session.run(f"CREATE INDEX FOR (n:{label}) ON (n.id)")
            except Exception:
                pass

        # --- Region / Place 노드 생성 (한국 공포 데이터 기반) ---
        print("\nCreating Region and Place nodes from Korean horror data...")
        korean_path = os.path.join(BASE_DIR, 'database', 'data', 'verified_korean_horror_master.json')
        if os.path.exists(korean_path):
            with open(korean_path, 'r', encoding='utf-8') as f:
                korean_data = json.load(f)

            region_map = {}
            for item in korean_data:
                region = item.get('region', '').strip()
                title = item.get('title', '').strip()
                if not region or not title:
                    continue
                if region not in region_map:
                    region_map[region] = []
                region_map[region].append(title)

            for region_name, stories in region_map.items():
                region_id = f"region_{normalize_string(region_name)}"
                session.run("""
                MERGE (r:Region {id: $id})
                SET r.name = $name
                """, id=region_id, name=region_name)

                for story_title in stories:
                    place_id = f"place_{normalize_string(story_title)}"
                    story_id = f"story_{normalize_string(story_title)}"
                    session.run("""
                    MERGE (p:Place {id: $pid})
                    SET p.name = $name
                    WITH p
                    MATCH (r:Region {id: $rid})
                    MERGE (r)-[:HAS_PLACE]->(p)
                    """, pid=place_id, name=story_title, rid=region_id)
                    session.run("""
                    MATCH (p:Place {id: $pid})
                    MATCH (s:Story {id: $sid})
                    MERGE (p)-[:OCCURRED_AT]->(s)
                    """, pid=place_id, sid=story_id)

            print(f"-> Created {len(region_map)} Region nodes with Place links.")

        # --- 본문 바인딩 ---
        print("\nBinding original content text to nodes...")
        docs_dir = os.path.join(BASE_DIR, 'database', 'data')
        preprocessing_dir = os.path.join(BASE_DIR, 'processing')

        # A. Korean master
        if os.path.exists(korean_path):
            print("-> Binding verified_korean_horror_master.json...")
            with open(korean_path, 'r', encoding='utf-8') as f:
                korean_data = json.load(f)
            story_updates, legend_updates = [], []
            for item in korean_data:
                title = item.get('title')
                content = item.get('content', '').strip()
                norm = normalize_string(title)
                if not content or not norm:
                    continue
                story_updates.append({"id": f"story_{norm}", "content": content})
                legend_updates.append({"id": f"legend_{norm}", "content": content})
                legend_updates.append({"id": f"yokai_{norm}", "content": content})

            session.run("""
            UNWIND $batch AS row MATCH (n:Story {id: row.id})
            SET n.body = CASE WHEN row.content <> '' THEN row.content ELSE n.body END
            """, batch=story_updates)
            session.run("""
            UNWIND $batch AS row MATCH (n:Legend {id: row.id})
            SET n.body = CASE WHEN row.content <> '' THEN row.content ELSE n.body END
            """, batch=legend_updates)
            session.run("""
            UNWIND $batch AS row MATCH (n:Yokai {id: row.id})
            SET n.body = CASE WHEN row.content <> '' THEN row.content ELSE n.body END
            """, batch=legend_updates)

        # B. Global mythology
        global_path = os.path.join(docs_dir, 'ultimate_global_mythology_1000.json')
        if os.path.exists(global_path):
            print("-> Binding ultimate_global_mythology_1000.json...")
            with open(global_path, 'r', encoding='utf-8') as f:
                global_data = json.load(f)
            global_updates = [
                {"id": f"legend_{normalize_string(item.get('name', ''))}", "desc": item.get('description', '')}
                for item in global_data
            ]
            session.run("""
            UNWIND $batch AS row MATCH (l:Legend {id: row.id})
            SET l.body = CASE WHEN row.desc <> '' THEN row.desc ELSE l.body END
            """, batch=global_updates)

        # C. Reddit horror stories
        reddit_path = os.path.join(docs_dir, 'global_horror_database.json')
        if os.path.exists(reddit_path):
            print("-> Binding global_horror_database.json (5000 items)...")
            with open(reddit_path, 'r', encoding='utf-8') as f:
                reddit_data = json.load(f)
            reddit_updates = [
                {"id": f"story_{normalize_string(item.get('title', ''))}", "body": item.get('full_content', item.get('text', ''))}
                for item in reddit_data[:5000] if normalize_string(item.get('title', ''))
            ]
            session.run("""
            UNWIND $batch AS row MATCH (s:Story {id: row.id})
            SET s.body = CASE WHEN row.body <> '' AND s.body IS NULL THEN row.body ELSE s.body END
            """, batch=reddit_updates)

        # D. SCP
        scp_path = os.path.join(docs_dir, 'preprocessed_scp.json')
        if os.path.exists(scp_path):
            print("-> Binding preprocessed_scp.json...")
            with open(scp_path, 'r', encoding='utf-8') as f:
                scp_data = json.load(f)
            scp_updates = [
                {"id": f"scp_{normalize_string(item.get('code', ''))}", "text": item.get('text', '')}
                for item in scp_data if normalize_string(item.get('code', ''))
            ]
            session.run("""
            UNWIND $batch AS row MATCH (n:SCP {id: row.id})
            SET n.text = CASE WHEN row.text <> '' THEN row.text ELSE n.text END
            """, batch=scp_updates)

        # E. DC인사이드
        dc_path = os.path.join(docs_dir, 'dcinside_horror_filtered.json')
        if os.path.exists(dc_path):
            print("-> Binding dcinside_horror_filtered.json...")
            with open(dc_path, 'r', encoding='utf-8') as f:
                dc_data = json.load(f)
            dc_updates = []
            for item in dc_data:
                title = item.get('title', '').strip()
                content = item.get('content', '')
                if not content:
                    continue
                display_title = title if title and title not in ('[경험]', '[괴담]', '[공포]', '[창작]', '[사건/사고]') else content[:30].strip() + '...'
                norm = normalize_string(display_title)
                if norm:
                    dc_updates.append({"id": f"story_{norm}", "body": content})
            session.run("""
            UNWIND $batch AS row MATCH (s:Story {id: row.id})
            SET s.body = CASE WHEN row.body <> '' AND s.body IS NULL THEN row.body ELSE s.body END
            """, batch=dc_updates)
            print(f"   DC인사이드 바인딩: {len(dc_updates)}건")

        # --- 엣지 로드 ---
        print("Importing Edges from edges.csv...")
        rel_types = ["RECORDED_IN", "WARDED_OFF_BY", "ORIGINATED_IN", "HAPPENED_IN", "POSTED_ON", "FEATURES", "LIVES_IN"]
        for r_type in rel_types:
            print(f"-> Linking: {r_type}")
            session.run(f"""
            LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
            WITH row WHERE row.type = '{r_type}'
            MATCH (source {{id: row.source}})
            MATCH (target {{id: row.target}})
            CREATE (source)-[r:{r_type}]->(target)
            """)

        print("\nVerifying imported counts:")
        for record in session.run("MATCH (n) RETURN labels(n) AS labels, count(n) AS cnt"):
            print(f"Label: {record['labels']} - Count: {record['cnt']}")
        for record in session.run("MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt"):
            print(f"Relationship: {record['rel_type']} - Count: {record['cnt']}")

    driver.close()
    print("Graph DB Import Completed Successfully!")


if __name__ == '__main__':
    run_import()
