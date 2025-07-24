import json
import os
import re
import subprocess
import requests
from mutagen import File as MutagenFile # type: ignore

# Path to your audio data file (JSON array or JS file)
AUDIO_DATA_PATH = r'z:\\Audiobook Organizer\\lunar-light\\src\\data\\audioData.js'
OUTPUT_PATH = AUDIO_DATA_PATH
COVER_DIR = r'z:\\Audiobook Organizer\\lunar-light\\public\\temp-covers'

os.makedirs(COVER_DIR, exist_ok=True)

def load_audio_items():
    with open(AUDIO_DATA_PATH, 'r', encoding='utf-8') as f:
        raw = f.read()
        match = re.search(r'(\[.*\])', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        else:
            raise Exception('Could not find JSON array in audioData.js')

def download_cover(cover_url, asin):
    if not cover_url:
        return ''
    ext = cover_url.split('.')[-1].split('?')[0]
    filename = f'{asin}.{ext}'
    filepath = os.path.join(COVER_DIR, filename)
    try:
        r = requests.get(cover_url, timeout=10)
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(r.content)
        print(f'[INFO] Downloaded cover to {filepath}')
        return f'/temp-covers/{filename}'
    except Exception as e:
        print(f'[ERROR] Downloading cover {cover_url}: {e}')
        return ''

def audible_api_cli(query):
    # Clean query: only letters and spaces
    def clean(s):
        return re.sub(r'[^a-zA-Z ]+', '', s)
    # Accepts query as dict: {asin, title, author, filename}
    if isinstance(query, dict):
        asin = query.get('asin')
        title_val = query.get('title')
        author_val = query.get('author')
        filename = query.get('filename')
    else:
        asin = None
        title_val = query
        author_val = None
        filename = None

    def run_query(q):
        print(f'[SEARCH QUERY] {q}')
        cli_cmd = [
            'audible', 'api', '/1.0/catalog/products',
            '-p', f'keywords={q}',
            '-p', 'num_results=10',
            '-p', 'response_groups=product_desc,product_attrs,media',
            '-f', 'json'
        ]
        try:
            result = subprocess.run(cli_cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            products = data.get('products', {})
            product_list = []
            if isinstance(products, dict):
                for asin, meta in products.items():
                    meta['asin'] = asin
                    product_list.append(meta)
            elif isinstance(products, list):
                for meta in products:
                    meta['asin'] = meta.get('asin', '')
                    product_list.append(meta)
            if not product_list:
                print('[WARN] No products found in API response.')
                return None
            return product_list
        except Exception as e:
            print(f'[ERROR] Audible API CLI: {e}')
        return None

    # 1. Search by ASIN if available
    if asin:
        result = run_query(asin)
        if result:
            return result
    # 2. Search by title/author
    if title_val or author_val:
        query = f'{title_val or ""} {author_val or ""}'.strip()
        query = clean(query)
        result = run_query(query)
        if result:
            return result
    # 3. Search by filename (letters only, spaces for non-letters)
    if filename:
        base = os.path.basename(filename)
        name = re.sub(r'[^a-zA-Z]+', ' ', base)
        name = name.strip()
        if name:
            result = run_query(name)
            if result:
                return result
    return None

def get_local_length_minutes(paths):
    total_seconds = 0
    for p in paths:
        try:
            audio = MutagenFile(p)
            if audio and audio.info:
                total_seconds += audio.info.length
        except Exception as e:
            print(f'[ERROR] Reading length for {p}: {e}')
    return round(total_seconds / 60, 2) if total_seconds else None

def write_as_js_module(items, path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('export const audioItems = ')
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write(';\n')

def main():
    items = load_audio_items()
    print(f'[INFO] Loaded {len(items)} audio items')
    if not items:
        print('[ERROR] No items found.')
        return
    for idx, item in enumerate(items):
        old = item.get('old', {})
        title = old.get('title', '')
        author = old.get('author', '')
        year = old.get('year', '')
        series = old.get('series', '')
        genre = old.get('genre', [])
        paths = item.get('paths', [])
        print(f'[INFO] Processing {idx+1}/{len(items)}: {title} - {author}')
        asin = old.get('asin', '')
        filename = paths[0] if paths else ''
        meta_list = audible_api_cli({'asin': asin, 'title': title, 'author': author, 'filename': filename})
        local_length = get_local_length_minutes(paths)
        best_meta = None
        best_diff = None
        if meta_list:
            # Find the match with the closest runtime_length_min
            for meta in meta_list:
                runtime_length = meta.get('runtime_length_min')
                if runtime_length and local_length:
                    diff = abs(runtime_length - local_length)
                    if best_diff is None or diff < best_diff:
                        best_diff = diff
                        best_meta = meta
            if not best_meta:
                best_meta = meta_list[0]
            meta = best_meta
            cover_url = meta.get('product_images', {}).get('500', '')
            asin = meta.get('asin', f'cover_{idx}')
            cover_path = download_cover(cover_url, asin)
            runtime_length = meta.get('runtime_length_min')
            subtitle = meta.get('subtitle', '')
            author_val = (
                meta.get('author', '') or
                (meta.get('authors', [{}])[0].get('name') if meta.get('authors') else author)
            )
            narrator_val = (
                (meta.get('narrators', [{}])[0].get('name') if meta.get('narrators') else '')
            )
            item['audible_raw'] = meta
            # --- Generate new paths in requested format ---
            def safe(val):
                return str(val or '').replace('/', '-').replace('\\', '-')
            # Use publication_name as fallback for series
            series_val = meta.get('series', None) or meta.get('publication_name', None) or series or meta.get('title', title)
            series_name = safe(series_val)
            book_title = safe(meta.get('title', title))
            # Try to get book number/position
            pos = meta.get('series_position') or meta.get('series_position_in_series') or meta.get('book_number') or meta.get('volume') or ''
            try:
                pos = int(float(pos))
            except Exception:
                pos = ''
            pos_str = f"{pos}-" if pos else ''
            # Year: try to get 4-digit year from release date
            year_val = meta.get('release_date', year)
            year_match = re.search(r'(\d{4})', str(year_val))
            year_str = year_match.group(1) if year_match else ''
            folder = f"{series_name}/{pos_str}{book_title}"
            if year_str:
                folder += f" ({year_str})"
            # If only one file, just use the book title
            old_paths = item.get('old', {}).get('paths', [])
            if len(old_paths) == 1:
                new_paths = [f"{folder}/{book_title}"]
            else:
                # Multi-part: add [Part XX] to each file
                new_paths = []
                for i, _ in enumerate(old_paths):
                    new_paths.append(f"{folder}/{book_title} [Part {i+1:02d}]")
            item['new'] = {
                'title': meta.get('title', title),
                'subtitle': subtitle,
                'author': author_val,
                'narrator': narrator_val,
                'year': meta.get('release_date', year),
                'coverImage': cover_path,
                'series': series_val,
                'genre': meta.get('categories', genre),
                'asin': asin,
                'audible_url': f'https://www.audible.com/pd/{asin}',
                'runtime_length_min': runtime_length,
                'length_match': abs(runtime_length - local_length) < 5 if (runtime_length and local_length) else None,
                'local_length_min': local_length,
                'paths': new_paths
            }
        else:
            item['new'] = {'local_length_min': local_length}
            print('[WARN] No Audible metadata found.')
    write_as_js_module(items, OUTPUT_PATH)
    print(f'[INFO] Wrote enriched data to {OUTPUT_PATH}')

if __name__ == '__main__':
    main()
