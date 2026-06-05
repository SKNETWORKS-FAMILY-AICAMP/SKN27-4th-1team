import openpyxl
import json
import os
import re

def clean_text(text):
    if not text:
        return ""
    # Replace the corrupted '' symbol often replacing single quotes/double quotes (usually due to encoding issues with CP1252 / UTF-8 clash)
    cleaned = str(text).replace("re", "'re").replace("s", "'s").replace("t", "'t").replace("ll", "'ll").replace("ve", "'ve").replace("d", "'d").replace("m", "'m")
    cleaned = cleaned.replace("", "'") # Catch-all for double quotes or remaining single quote symbols
    # Normalize duplicate whitespace
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    cleaned = re.sub(r'\s*\n+\s*', '\n', cleaned)
    return cleaned.strip()

def preprocess_creepypasta():
    xlsx_path = 'crawler/creepypastas.xlsx'
    output_path = 'graph_source_data/preprocessed_creepypastas.json'
    
    if not os.path.exists(xlsx_path):
        print(f"Error: {xlsx_path} not found.")
        return
        
    print("Loading creepypastas.xlsx (read-only)...")
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    sheet = wb.active
    
    cleaned_items = []
    
    # Headers: ('story_name', 'average_rating', 'tags', 'body', 'estimated_reading_time', 'publish_date', 'categories')
    rows_iter = sheet.iter_rows(values_only=True)
    headers = next(rows_iter)
    
    for row in rows_iter:
        if not row or len(row) < 7:
            continue
            
        story_name = row[0]
        avg_rating = row[1]
        tags_str = row[2]
        body = row[3]
        reading_time = row[4]
        categories_str = row[6]
        
        if not story_name or not body:
            continue
            
        # Filter for high quality / highly rated creepypastas to maintain high-quality nodes
        try:
            rating = float(avg_rating)
        except (ValueError, TypeError):
            rating = 0.0
            
        if rating < 5.0: # Keep stories rated 5.0 or higher
            continue
            
        # Parse tags
        tags = []
        if tags_str:
            tags = [t.strip().lower() for t in tags_str.replace('\n', '').split(',') if t.strip()]
            
        # Parse categories
        categories = []
        if categories_str:
            categories = [c.strip() for c in categories_str.replace('\n', '').split(',') if c.strip()]
            
        # Filter tags and categories from metadata noise
        excluded = {'creepypasta', 'story', 'horror', 'stories', 'creepy'}
        tags = [t for t in tags if t not in excluded]
        categories = [c for c in categories if c.lower() not in excluded]
        
        # Clean text content
        story_name_clean = clean_text(story_name)
        body_clean = clean_text(body)
        
        # Cap body size to keep embeddings/parsing memory efficient
        if len(body_clean) > 8000:
            body_clean = body_clean[:8000] + " ... [TRUNCATED]"
            
        cleaned_items.append({
            "title": story_name_clean,
            "rating": rating,
            "tags": tags,
            "body": body_clean,
            "reading_time": reading_time,
            "categories": categories
        })
        
    wb.close()
    
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as out_f:
        json.dump(cleaned_items, out_f, ensure_ascii=False, indent=2)
        
    print("Preprocessing Creepypasta completed successfully!")
    print(f"Total cleaned and filtered stories: {len(cleaned_items)}")
    print(f"Saved into: {output_path}")

if __name__ == '__main__':
    preprocess_creepypasta()
