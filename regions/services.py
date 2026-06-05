"""Business logic for the regions app."""
import os
import socket
from neo4j import GraphDatabase

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

def query_region_relations(region_name):
    """
    Queries Neo4j for Places and Creepypastas associated with a specific Region name.
    Matches path: (r:Region)-[:HAS_PLACE]->(p:Place)-[:OCCURRED_AT]-(c)
    """
    if not region_name:
        return []

    driver = get_neo4j_driver()
    places_dict = {}

    # Cypher query to retrieve place node and related stories/legends
    cypher_query = """
    MATCH (r:Region)
    WHERE toLower(r.name) CONTAINS toLower($region)
    MATCH (r)-[:HAS_PLACE]->(p:Place)
    OPTIONAL MATCH (p)-[:OCCURRED_AT]-(c)
    WHERE c:Story OR c:Legend OR c:SCP
    RETURN p.name AS place_name,
           p.description AS place_description,
           collect(DISTINCT {
               id: c.id,
               name: c.name,
               type: labels(c)[0],
               preview: substring(coalesce(c.body, c.text, ''), 0, 100)
           }) AS stories
    LIMIT 25
    """

    try:
        with driver.session() as session:
            records = session.run(cypher_query, region=region_name.strip())
            for r in records:
                place = r['place_name']
                # Filter out null elements from collector if any
                stories = [s for s in r['stories'] if s.get('id') is not None]
                places_dict[place] = {
                    'name': place,
                    'description': r['place_description'] if r['place_description'] else '기록 미상의 장소.',
                    'stories': stories
                }
    except Exception as e:
        print(f"Error querying Region details from Neo4j: {e}")
    finally:
        driver.close()

    return list(places_dict.values())

