import json
import csv
import sys
import os
import re

def clean_name(n):
    return str(n).strip().replace('"', '').replace("'", "")

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("Processing managed JSON files (KOREAN MASTER, GLOBAL MASTER, REDDIT STORIES) to build nodes.csv and edges.csv...")
    
    source_dir = 'graph_source_data'
    
    # Check if files exist
    korean_path = os.path.join(source_dir, 'verified_korean_horror_master.json')
    global_path = os.path.join(source_dir, 'ultimate_global_mythology_1000.json')
    global_db_path = os.path.join(source_dir, 'global_horror_database.json')
    
    # Store unique Nodes and Edges
    nodes = {}  # id -> {id, name, label}
    edges = set()  # set of (source, target, type)
    
    # Tracking sets to prevent duplicates across files
    seen_stories = set()  # Normalized titles of scary stories/episodes
    
    def normalize_string(s):
        return re.sub(r'[^a-zA-Z0-9가-힣]', '', str(s)).lower()

    def add_legend_node(name, label_type):
        norm = normalize_string(name)
        if not norm:
            return None
        node_id = f"legend_{norm}"
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": clean_name(name),
                "label": label_type.capitalize()
            }
        return node_id

    def add_story_node(title):
        norm = normalize_string(title)
        if not norm or norm in seen_stories:
            return None
        seen_stories.add(norm)
        node_id = f"story_{norm}"
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": clean_name(title),
                "label": "Story"
            }
        return node_id

    def add_general_node(name, node_type):
        norm = normalize_string(name)
        if not norm:
            return None
        node_id = f"{node_type}_{norm}"
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "name": clean_name(name),
                "label": node_type.capitalize()
            }
        return node_id

    # 1. Parse Korean Master Dataset (224 entries)
    if os.path.exists(korean_path):
        print("-> Parsing verified_korean_horror_master.json...")
        with open(korean_path, 'r', encoding='utf-8') as f:
            korean_data = json.load(f)
            
        yokai_list = {
            "도깨비", "구미호", "이무기", "불가사리", "해태", "삼족오", "오니", "텐구",
            "카파", "용", "야차", "나찰", "조왕신", "성주신", "삼신", "터주신",
            "현무", "청룡", "백호", "주작", "기린", "봉황", "종규", "염라대왕",
            "천구", "비휴", "도철", "나가", "가루다", "야크샤", "라크샤사", "베탈", "피샤차"
        }
        
        for item in korean_data:
            title = item.get('title')
            content = item.get('content', '')
            source = item.get('source', '')
            region = item.get('region', '한국')
            
            # Identify if it is an Episode/Story or a Yokai/Legend
            if source == 'thering' or "에피소드" in title or "이야기" in title or re.search(r'제\d+화', title):
                node_id = add_story_node(title)
                if not node_id:
                    continue
                # Locations
                locations = []
                if "학교" in content: locations.append("학교")
                if "도로" in content or "터널" in content or "고속도로" in content: locations.append("도로/터널")
                if "아파트" in content or "엘리베이터" in content: locations.append("아파트")
                if "산" in content or "숲" in content: locations.append("산/숲")
                if "병원" in content: locations.append("병원")
                for loc in locations:
                    loc_id = add_general_node(loc, "location")
                    edges.add((node_id, loc_id, "HAPPENED_IN"))
                # Source
                src_id = add_general_node("잠들 수 없는 밤의 기묘한 이야기", "source")
                edges.add((node_id, src_id, "POSTED_ON"))
            else:
                label_type = "yokai" if title in yokai_list else "legend"
                node_id = add_legend_node(title, label_type)
                if not node_id:
                    continue
                origin_id = add_general_node(region, "origin")
                edges.add((node_id, origin_id, "ORIGINATED_IN"))
                
                # Locations
                locations = []
                if "학교" in content: locations.append("학교")
                if "도로" in content or "터널" in content or "고속도로" in content: locations.append("도로/터널")
                if "아파트" in content or "엘리베이터" in content: locations.append("아파트")
                if "산" in content or "숲" in content: locations.append("산/숲")
                if "화장실" in content: locations.append("화장실")
                if "병원" in content: locations.append("병원")
                if "집 안" in content or "주거지" in content: locations.append("주거지")
                for loc in locations:
                    loc_id = add_general_node(loc, "location")
                    edges.add((node_id, loc_id, "LIVES_IN"))
                
                # Weaknesses
                weaknesses = []
                if "소금" in content: weaknesses.append("소금")
                if "팥" in content: weaknesses.append("붉은 팥")
                if "부적" in content: weaknesses.append("부적")
                if "소음" in content or "소리" in content: weaknesses.append("소음/소리")
                for wk in weaknesses:
                    wk_id = add_general_node(wk, "countermeasure")
                    edges.add((node_id, wk_id, "WARDED_OFF_BY"))
                
                src_name = "나무위키" if source == "namu_wiki" else "위키백과"
                src_id = add_general_node(src_name, "source")
                edges.add((node_id, src_id, "RECORDED_IN"))

    # 2. Parse Global Master Dataset (1,016 entries)
    if os.path.exists(global_path):
        print("-> Parsing ultimate_global_mythology_1000.json...")
        with open(global_path, 'r', encoding='utf-8') as f:
            global_data = json.load(f)
        for item in global_data:
            name = item.get('name')
            origin = item.get('origin', 'Global')
            habitats = item.get('habitats', [])
            weakness = item.get('weakness', '')
            
            node_id = add_legend_node(name, "legend")
            if not node_id:
                continue
            origin_id = add_general_node(origin, "origin")
            edges.add((node_id, origin_id, "ORIGINATED_IN"))
            for hab in habitats:
                hab_id = add_general_node(hab, "location")
                edges.add((node_id, hab_id, "LIVES_IN"))
            if weakness and weakness != "None":
                for wk in re.split(r',|및', weakness):
                    wk = wk.strip()
                    if wk:
                        wk_id = add_general_node(wk, "countermeasure")
                        edges.add((node_id, wk_id, "WARDED_OFF_BY"))
            src_id = add_general_node("Wikipedia", "source")
            edges.add((node_id, src_id, "RECORDED_IN"))

    # 3. Parse global_horror_database.json (27,232 entries)
    if os.path.exists(global_db_path):
        print("-> Parsing global_horror_database.json...")
        with open(global_db_path, 'r', encoding='utf-8') as f:
            global_db_data = json.load(f)
        for item in global_db_data[:3000]:  # Cap at 3000 to keep performance optimal
            title = item.get('title')
            region = item.get('region', 'Global')
            matched_habitats = item.get('matched_habitats', [])
            matched_entities = item.get('matched_entities', [])
            source_name = item.get('source', 'Reddit')
            
            node_id = add_story_node(title)
            if not node_id:
                continue
                
            origin_id = add_general_node(region, "origin")
            edges.add((node_id, origin_id, "ORIGINATED_IN"))
            for hab in matched_habitats:
                hab_id = add_general_node(hab, "location")
                edges.add((node_id, hab_id, "HAPPENED_IN"))
            for ent in matched_entities:
                ent_id = add_legend_node(ent, "legend")
                if ent_id:
                    edges.add((node_id, ent_id, "FEATURES"))
            src_id = add_general_node(source_name, "source")
            edges.add((node_id, src_id, "POSTED_ON"))

    # 4. Parse preprocessed_scp.json (995 entries)
    scp_path = os.path.join(source_dir, 'preprocessed_scp.json')
    if os.path.exists(scp_path):
        print("-> Parsing preprocessed_scp.json...")
        with open(scp_path, 'r', encoding='utf-8') as f:
            scp_data = json.load(f)
            
        # Common cross-references between SCPs and Korean/Global legends (e.g. gumiho / nine-tailed fox)
        cross_ref_mapping = {
            "gumiho": ["구미호", "nine-tailed fox"],
            "kumiho": ["구미호", "nine-tailed fox"],
            "dokkebbi": ["도깨비", "goblin"],
            "tokebbi": ["도깨비", "goblin"],
            "imugi": ["이무기", "proto-dragon"],
            "vampire": ["뱀파이어", "흡혈귀"],
            "werewolf": ["늑대인간"],
            "ghost": ["유령", "귀신"],
            "demon": ["악마", "사탄"],
            "dragon": ["용", "드래곤"]
        }
        
        for item in scp_data:
            code = item.get('code')
            title = item.get('title')
            text = item.get('text', '')
            obj_class = item.get('object_class', 'Unknown')
            tags = item.get('tags', [])
            
            # Add SCP node
            scp_id = f"scp_{normalize_string(code)}"
            if scp_id not in nodes:
                nodes[scp_id] = {
                    "id": scp_id,
                    "name": f"{code} (\"{clean_name(title)}\")",
                    "label": "SCP"
                }
                
            # Origin (SCP Foundation)
            origin_id = add_general_node("SCP Foundation", "origin")
            edges.add((scp_id, origin_id, "ORIGINATED_IN"))
            
            # Object Class as Tag / Category node
            class_id = add_general_node(obj_class, "countermeasure") # Categorized into countermeasure constraints
            edges.add((scp_id, class_id, "WARDED_OFF_BY"))
            
            # Source
            src_id = add_general_node("SCP Foundation Wiki", "source")
            edges.add((scp_id, src_id, "RECORDED_IN"))
            
            # Tags as Locations / Conceptual filters
            for tag in tags:
                tag_id = add_general_node(tag, "location")
                edges.add((scp_id, tag_id, "LIVES_IN"))
                
            # Cross referencing with existing yokai/legends based on text and tags
            for key, keywords in cross_ref_mapping.items():
                if any(kw.lower() in text.lower() or kw.lower() in title.lower() or key in tags for kw in keywords):
                    # Link to corresponding legend
                    legend_norm = normalize_string(keywords[0])
                    legend_id = f"legend_{legend_norm}"
                    # Try to link if target node exists in graph
                    edges.add((scp_id, legend_id, "FEATURES"))

    # 5. Parse preprocessed_creepypastas.json (3,387 entries)
    cp_path = os.path.join(source_dir, 'preprocessed_creepypastas.json')
    if os.path.exists(cp_path):
        print("-> Parsing preprocessed_creepypastas.json...")
        with open(cp_path, 'r', encoding='utf-8') as f:
            cp_data = json.load(f)
            
        # Common cross-references between Creepypastas and Korean/Global legends (e.g. Slenderman, Jeff, Yokai)
        cross_ref_mapping = {
            "slenderman": ["슬렌더맨", "slender man"],
            "jeff": ["제프", "jeff the killer"],
            "eyeless": ["아이리스", "eyeless jack"],
            "dokkebbi": ["도깨비", "goblin"],
            "gumiho": ["구미호", "nine-tailed fox"],
            "ghost": ["유령", "귀신"],
            "vampire": ["뱀파이어", "흡혈귀"],
            "werewolf": ["늑대인간"],
            "demon": ["악마", "사탄"]
        }
        
        for item in cp_data:
            title = item.get('title')
            body = item.get('body', '')
            tags = item.get('tags', [])
            categories = item.get('categories', [])
            
            # Add Creepypasta node as Story
            node_id = add_story_node(title)
            if not node_id:
                continue
                
            # Origin
            origin_id = add_general_node("Global", "origin")
            edges.add((node_id, origin_id, "ORIGINATED_IN"))
            
            # Categories as locations/filters
            for cat in categories:
                cat_id = add_general_node(cat, "location")
                edges.add((node_id, cat_id, "HAPPENED_IN"))
                
            # Tags as location tags
            for tag in tags:
                tag_id = add_general_node(tag, "location")
                edges.add((node_id, tag_id, "HAPPENED_IN"))
                
            # Source
            src_id = add_general_node("Creepypasta Wiki", "source")
            edges.add((node_id, src_id, "POSTED_ON"))
            
            # Cross-referencing to Yokai/Legends
            for key, keywords in cross_ref_mapping.items():
                if any(kw.lower() in body.lower() or kw.lower() in title.lower() or key in tags for kw in keywords):
                    legend_norm = normalize_string(keywords[0])
                    legend_id = f"legend_{legend_norm}"
                    edges.add((node_id, legend_id, "FEATURES"))

    # Write Nodes CSV
    with open('nodes.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "label"])
        for node in nodes.values():
            writer.writerow([node["id"], node["name"], node["label"]])

    # Write Edges CSV
    with open('edges.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "type"])
        for edge in edges:
            writer.writerow(edge)

    print(f"\n--- Master Global Graph DB Build Complete (Exorcism Excluded) ---")
    print(f"Total Nodes: {len(nodes)} (saved in nodes.csv)")
    print(f"Total Edges: {len(edges)} (saved in edges.csv)")

if __name__ == '__main__':
    main()
