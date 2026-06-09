"""Business logic for the regions app."""
import os
import socket
from neo4j import GraphDatabase


def get_neo4j_driver():
    """Dynamically resolves host name to avoid Docker container vs localhost confusion, then returns the Neo4j driver."""
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'neo4j_password')

    try:
        host_part = uri.split("//")[1].split(":")[0]
        socket.gethostbyname(host_part)
    except Exception:
        uri = f"bolt://localhost:7687"

    return GraphDatabase.driver(uri, auth=(user, password))


def get_cities_by_region(region_name):
    """Region 아래 City 노드와 스토리 목록을 반환한다."""
    driver = get_neo4j_driver()
    result = []
    try:
        with driver.session() as session:
            records = session.run("""
            MATCH (r:Region {name: $region})-[:HAS_CITY]->(c:City)-[:HAS_STORY]->(s:Story)
            RETURN c.name AS city,
                   collect({id: s.id, name: s.name,
                             preview: substring(coalesce(s.body, s.text, ''), 0, 100)
                   }) AS stories
            ORDER BY c.name
            """, region=region_name)
            for rec in records:
                result.append({
                    'city': rec['city'],
                    'stories': list(rec['stories']),
                })
    except Exception as e:
        print(f"Error fetching cities: {e}")
    finally:
        driver.close()
    return result


def get_story_body(story_id):
    """스토리 전체 본문을 반환한다. Story/Legend/SCP 모두 조회."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run("""
            MATCH (s {id: $id})
            WHERE s:Story OR s:Legend OR s:SCP
            RETURN s.name AS name, coalesce(s.body, s.text, '본문 없음') AS body,
                   labels(s)[0] AS type
            """, id=story_id)
            rec = result.single()
            if rec:
                return {'name': rec['name'], 'body': rec['body'], 'type': rec['type']}
    except Exception as e:
        print(f"Error fetching story: {e}")
    finally:
        driver.close()
    return None


def get_region_list():
    """Returns all Region and Origin nodes with story counts."""
    driver = get_neo4j_driver()
    regions = []
    try:
        with driver.session() as session:
            records = session.run("""
            MATCH (r:Region)
            OPTIONAL MATCH (r)-[:HAS_PLACE]->(p:Place)
            RETURN r.name AS name, count(p) AS place_count
            UNION
            MATCH (o:Origin)
            WHERE NOT EXISTS { MATCH (r2:Region {name: o.name}) }
            OPTIONAL MATCH (n)-[:ORIGINATED_IN]->(o)
            WHERE n:Legend OR n:Story OR n:SCP
            RETURN o.name AS name, count(n) AS place_count
            ORDER BY place_count DESC
            """)
            for r in records:
                regions.append({'name': r['name'], 'place_count': r['place_count']})
    except Exception as e:
        print(f"Error fetching region list: {e}")
    finally:
        driver.close()
    return regions


def query_region_relations(region_name):
    """
    Origin 기반으로 해당 지역의 스토리/레전드를 조회한다.
    """
    if not region_name:
        return []

    driver = get_neo4j_driver()
    places_dict = {}

    try:
        with driver.session() as session:
            records = session.run("""
            MATCH (o:Origin)
            WHERE toLower(o.name) = toLower($region)
            MATCH (c)-[:ORIGINATED_IN]->(o)
            WHERE (c:Legend OR c:Story)
            AND c.body IS NOT NULL AND c.body <> ''
            WITH o, c ORDER BY CASE WHEN c:Story THEN 0 ELSE 1 END, c.name
            RETURN o.name AS place_name,
                   collect({
                       id: c.id,
                       name: c.name,
                       type: labels(c)[0],
                       preview: substring(coalesce(c.body, c.text, ''), 0, 100)
                   }) AS stories
            """, region=region_name.strip())

            for r in records:
                place = r['place_name']
                stories = [s for s in r['stories'] if s.get('id') is not None]
                if stories:
                    places_dict[place] = {
                        'name': place,
                        'description': '기록 미상의 장소.',
                        'stories': stories
                    }

    except Exception as e:
        print(f"Error querying Region details from Neo4j: {e}")
    finally:
        driver.close()

    return list(places_dict.values())

