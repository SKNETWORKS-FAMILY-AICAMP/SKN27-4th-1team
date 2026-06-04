import csv
import re
import json
import os
import sys

# Increase CSV field limit for large text blocks in SCP dataset
csv.field_size_limit(10000000)

def preprocess_scp():
    csv_path = 'crawler/archive (3)/scp6999.csv'
    output_path = 'graph_source_data/preprocessed_scp.json'
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    print("Starting preprocessing of SCP dataset...")
    
    cleaned_items = []
    
    # Precompile Regex Patterns
    redacted_pattern = re.compile(r'█{2,}')
    newlines_pattern = re.compile(r'\s*\n+\s*')
    spaces_pattern = re.compile(r' {2,}')
    
    # Class extraction pattern: tries to find "Object Class: Safe/Euclid/Keter" etc.
    class_pattern = re.compile(r'Object Class:\s*([A-Za-z0-9\-]+)', re.IGNORECASE)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        # Headers map: ['code', 'title', 'text', 'image captions', 'rating', 'state', 'tags', 'link']
        for row in reader:
            if len(row) < 8:
                continue
                
            code = row[0].strip()
            title = row[1].strip()
            text = row[2]
            rating_str = row[4].strip()
            state = row[5].strip().lower()
            tags_str = row[6].strip()
            link = row[7].strip()
            
            # 1. State Filter (only active documents)
            if state != 'active':
                continue
                
            # 2. General Notice dummy filter (memetic kill agent notice only)
            if "memetic kill agent" in text.lower() and len(text) < 1500 and "GENERAL NOTICE" in text:
                continue
                
            # 3. Clean Text
            # Replace blackout blocks (█████) with '[REDACTED_CONFIDENTIAL]'
            text_cleaned = redacted_pattern.sub('[REDACTED_CONFIDENTIAL]', text)
            
            # Normalize excessive spacing and newlines
            text_cleaned = newlines_pattern.sub('\n', text_cleaned)
            text_cleaned = spaces_pattern.sub(' ', text_cleaned)
            text_cleaned = text_cleaned.strip()
            
            # 4. Extract Object Class
            class_match = class_pattern.search(text_cleaned)
            object_class = class_match.group(1).strip().capitalize() if class_match else "Unknown"
            
            # Normalize object class if it has unexpected trailing content
            if len(object_class) > 20:
                object_class = "Unknown"
            
            # Parse tags and clean them
            raw_tags = []
            # Handle potential stringified list or space-separated tags inside the string
            cleaned_tag_str = tags_str.replace('[', '').replace(']', '').replace("'", "").replace('"', '')
            # Split by whitespace or comma
            for t in re.split(r'[\s,]+', cleaned_tag_str):
                t = t.strip().lower()
                if t:
                    raw_tags.append(t)
            
            # Filter out system tags that don't carry descriptive value
            excluded_tags = {'scp', '_licensebox', '_cc', 'alive', 'historical'}
            tags = [t for t in raw_tags if t not in excluded_tags and not t.startswith('_')]
            
            # Cap rating parsing
            try:
                rating = int(rating_str)
            except ValueError:
                rating = 0
                
            # Keep items with valid/positive rating and series 1 (SCP-001 to SCP-999) to prevent performance issues
            # We check the code format, e.g., SCP-011 or SCP-999.
            code_num_match = re.search(r'SCP-(\d+)', code, re.IGNORECASE)
            if code_num_match:
                code_num = int(code_num_match.group(1))
                # Only keep Series 1 for optimized hybrid RAG database size
                if code_num > 1000:
                    continue
            else:
                continue
                
            cleaned_items.append({
                "code": code,
                "title": title,
                "text": text_cleaned,
                "object_class": object_class,
                "rating": rating,
                "tags": tags,
                "link": link
            })
            
    # Save preprocessed output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as out_f:
        json.dump(cleaned_items, out_f, ensure_ascii=False, indent=2)
        
    print(f"Preprocessing finished successfully!")
    print(f"Total processed and cleaned active SCP items (Series 1): {len(cleaned_items)}")
    print(f"Saved into: {output_path}")

if __name__ == '__main__':
    preprocess_scp()
