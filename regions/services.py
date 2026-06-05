"""Business logic for the regions app."""
import os
import socket
from neo4j import GraphDatabase

# 지역별 키워드 맵 — 본문에서 해당 키워드가 나오면 그 도시/지역으로 분류
REGION_CITY_KEYWORDS = {
    '한국': {
        '서울':  ['서울', '한강', '명동', '강남', '홍대', '신촌', '종로', '잠실', '이태원', '마포'],
        '인천':  ['인천', '송도', '부평'],
        '부산':  ['부산', '해운대', '광안리', '남포동'],
        '대구':  ['대구', '동성로'],
        '대전':  ['대전', '둔산', '유성'],
        '광주':  ['광주'],
        '울산':  ['울산'],
        '경기':  ['수원', '성남', '고양', '용인', '안양', '부천', '의정부', '파주', '평택'],
        '강원':  ['강릉', '춘천', '원주', '속초', '설악', '동해'],
        '충청':  ['청주', '천안', '충북', '충남', '세종'],
        '전라':  ['전주', '목포', '여수', '순천', '전북', '전남'],
        '경상':  ['경주', '포항', '창원', '진주', '경북', '경남', '안동'],
        '제주':  ['제주', '한라산', '서귀포'],
    },
    '일본': {
        '도쿄':   ['도쿄', '도쿄도'],
        '교토':   ['교토'],
        '나라':   ['나라'],
        '홋카이도': ['홋카이도'],
        '오사카': ['오사카'],
        '오키나와': ['오키나와'],
    },
    '중국': {
        '홍콩': ['홍콩'],
        '베이징': ['베이징'],
        '상하이': ['상하이'],
    },
    '기타': {
        '멕시코': ['멕시코'],
        '영국':   ['런던', '영국'],
        '프랑스': ['파리', '프랑스'],
        '이집트': ['이집트'],
    },
}

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

def build_city_nodes():
    """
    Region 노드 아래에 City 노드를 생성하고 스토리를 연결한다.
    키워드 매칭으로 스토리 본문을 스캔해 도시를 분류한다.
    이미 City 노드가 있으면 덮어쓴다.
    """
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            for region_name, city_map in REGION_CITY_KEYWORDS.items():
                # 해당 Region 아래 모든 스토리 본문 가져오기
                records = list(session.run("""
                MATCH (r:Region)-[:HAS_PLACE]->(p:Place)-[:OCCURRED_AT]->(s:Story)
                WHERE r.name = $region
                RETURN s.id AS id, s.name AS name,
                       coalesce(s.body, s.text, '') AS body,
                       substring(coalesce(s.body, s.text, ''), 0, 100) AS preview
                """, region=region_name))

                if not records:
                    continue

                # 도시별로 스토리 분류
                city_stories = {city: [] for city in city_map}
                city_stories['기타'] = []

                for rec in records:
                    text = (rec['body'] or '') + (rec['name'] or '')
                    matched = False
                    for city, keywords in city_map.items():
                        if any(kw in text for kw in keywords):
                            city_stories[city].append({
                                'id': rec['id'], 'name': rec['name'], 'preview': rec['preview']
                            })
                            matched = True
                            break
                    if not matched:
                        city_stories['기타'].append({
                            'id': rec['id'], 'name': rec['name'], 'preview': rec['preview']
                        })

                # Neo4j에 City 노드 생성 및 연결
                for city_name, stories in city_stories.items():
                    if not stories:
                        continue
                    city_id = f"city_{region_name}_{city_name}"
                    session.run("""
                    MATCH (r:Region {name: $region})
                    MERGE (c:City {id: $city_id})
                    SET c.name = $city_name, c.region = $region
                    MERGE (r)-[:HAS_CITY]->(c)
                    """, region=region_name, city_id=city_id, city_name=city_name)

                    for story in stories:
                        session.run("""
                        MATCH (c:City {id: $city_id})
                        MATCH (s:Story {id: $story_id})
                        MERGE (c)-[:HAS_STORY]->(s)
                        """, city_id=city_id, story_id=story['id'])

        print("City 노드 구축 완료")
    except Exception as e:
        print(f"City 노드 구축 실패: {e}")
    finally:
        driver.close()


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


def city_nodes_exist():
    """City 노드가 이미 존재하는지 확인한다."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run("MATCH (c:City) RETURN count(c) AS cnt")
            return result.single()['cnt'] > 0
    except Exception:
        return False
    finally:
        driver.close()


def get_story_body(story_id):
    """스토리 전체 본문을 반환한다."""
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run("""
            MATCH (s:Story {id: $id})
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
    """Returns all Region nodes with place counts."""
    driver = get_neo4j_driver()
    regions = []
    try:
        with driver.session() as session:
            records = session.run("""
            MATCH (r:Region)
            OPTIONAL MATCH (r)-[:HAS_PLACE]->(p:Place)
            RETURN r.name AS name, count(p) AS place_count
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

