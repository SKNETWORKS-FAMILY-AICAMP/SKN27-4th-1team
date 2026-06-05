import os
import re
import zipfile
import shutil

def run_migration():
    project_dir = "C:/dev/project/SKN27-4th-1team"
    zip_path = os.path.join(project_dir, "templates/괴담.zip")
    
    if not os.path.exists(zip_path):
        print(f"Error: Zip file not found at {zip_path}")
        return
        
    temp_extract_dir = os.path.join(project_dir, "templates/temp_extract_goei")
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
        
    print("Extracting 괴담.zip...")
    with zipfile.ZipFile(zip_path, 'r') as ref:
        ref.extractall(temp_extract_dir)
        
    # Mapping for HTML Templates
    html_mapping = {
        "index.html": "templates/archive/index.html",
        "chatbot.html": "templates/archive/sillokgwan.html", # 기록 열람실 (Chatbot.html)
        "archive.html": "templates/archive/geumgirok.html",   # 금기 자료실 (Archive.html)
        "login.html": "templates/accounts/login.html",
        "register.html": "templates/accounts/signup.html",
        "mypage.html": "templates/accounts/mygirok.html",
        "storymaker.html": "templates/generator/goeijejoso.html",
        "community.html": "templates/post/mokgyeokgirok.html",
        "regioninfo.html": "templates/regions/jidogam.html"
    }
    
    # Destination directories for static assets
    static_css_dir = os.path.join(project_dir, "static/css")
    static_js_dir = os.path.join(project_dir, "static/js")
    static_fonts_dir = os.path.join(project_dir, "static/fonts")
    static_images_dir = os.path.join(project_dir, "static/images")
    static_audio_dir = os.path.join(project_dir, "static/audio")
    
    os.makedirs(static_css_dir, exist_ok=True)
    os.makedirs(static_js_dir, exist_ok=True)
    os.makedirs(static_fonts_dir, exist_ok=True)
    os.makedirs(static_images_dir, exist_ok=True)
    os.makedirs(static_audio_dir, exist_ok=True)
    
    extracted_root = os.path.join(temp_extract_dir, "괴담")
    
    # 1. Migrate Static Assets
    print("Moving static files to static/...")
    
    # CSS
    styles_src = os.path.join(extracted_root, "styles.css")
    if os.path.exists(styles_src):
        # We need to replace background-image: url('images/...') paths inside CSS
        with open(styles_src, 'r', encoding='utf-8') as f:
            css_content = f.read()
        # In Django CSS, static references inside CSS are handled relative to the CSS location,
        # or we can point to '../images/...' since css is in static/css and images is in static/images
        css_content = re.sub(r"url\(['\"]?images/([^'\")]+)['\"]?\)", r"url('../images/\1')", css_content)
        with open(os.path.join(static_css_dir, "styles.css"), 'w', encoding='utf-8') as f:
            f.write(css_content)
            
    # JS
    js_src = os.path.join(extracted_root, "flicker.js")
    if os.path.exists(js_src):
        with open(js_src, 'r', encoding='utf-8') as f:
            js_content = f.read()
        # Replace 'sounds/' paths with '/static/audio/' in JS file
        js_content = js_content.replace("'sounds/", "'/static/audio/")
        js_content = js_content.replace('"sounds/', '"/static/audio/')
        with open(os.path.join(static_js_dir, "flicker.js"), 'w', encoding='utf-8') as f:
            f.write(js_content)
            
    # Fonts
    fonts_src_dir = os.path.join(extracted_root, "fonts")
    if os.path.exists(fonts_src_dir):
        for font_file in os.listdir(fonts_src_dir):
            shutil.copy2(os.path.join(fonts_src_dir, font_file), os.path.join(static_fonts_dir, font_file))
            
    # Images
    images_src_dir = os.path.join(extracted_root, "images")
    if os.path.exists(images_src_dir):
        for img_file in os.listdir(images_src_dir):
            shutil.copy2(os.path.join(images_src_dir, img_file), os.path.join(static_images_dir, img_file))
            
    # Sounds / Audio
    sounds_src_dir = os.path.join(extracted_root, "sounds")
    if os.path.exists(sounds_src_dir):
        for snd_file in os.listdir(sounds_src_dir):
            shutil.copy2(os.path.join(sounds_src_dir, snd_file), os.path.join(static_audio_dir, snd_file))
            
    # 2. Migrate and Convert HTML Templates to Django format
    print("Migrating and converting HTML files to templates/...")
    
    def convert_html_to_django(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
            
        # Add {% load static %} at the top
        if "{% load static %}" not in html:
            html = "{% load static %}\n" + html
            
        # Replace styles.css
        html = re.sub(r'href=["\']styles\.css["\']', 'href="{% static \'css/styles.css\' %}"', html)
        
        # Replace flicker.js
        html = re.sub(r'src=["\']flicker\.js["\']', 'src="{% static \'js/flicker.js\' %}"', html)
        
        # Replace images/ references in src
        html = re.sub(r'src=["\']images/([^"\']+)["\']', 'src="{% static \'images/\\1\' %}"', html)
        
        # Replace sounds/ references
        html = html.replace('"sounds/', '"/static/audio/')
        html = html.replace("'sounds/", "'/static/audio/")
        
        # Replace inline styles background-image: url('images/...')
        html = re.sub(r"url\(['\"]?images/([^'\")]+)['\"]?\)", r"url('{% static 'images/\1' %}')", html)
        
        return html

    for src_name, dest_rel_path in html_mapping.items():
        src_path = os.path.join(extracted_root, src_name)
        if os.path.exists(src_path):
            converted_html = convert_html_to_django(src_path)
            dest_abs_path = os.path.join(project_dir, dest_rel_path)
            # Make sure parent directory exists
            os.makedirs(os.path.dirname(dest_abs_path), exist_ok=True)
            with open(dest_abs_path, 'w', encoding='utf-8') as f:
                f.write(converted_html)
            print(f"-> Migrated {src_name} to {dest_rel_path}")
            
    # Clean up temp extraction folder
    shutil.rmtree(temp_extract_dir)
    print("\n--- Template Migration and Path Conversion Completed Successfully! ---")

if __name__ == '__main__':
    run_migration()
