import json
import os
import re
import subprocess

AUDIO_DATA_PATH = r'z:\\Audiobook Organizer\\lunar-light\\src\\data\\audioData.js'
OUTPUT_PATH = r'z:\\Audiobook Organizer\\lunar-light\\src\\data\\audibleMetadataDump.json'

def load_audio_items():
    with open(AUDIO_DATA_PATH, 'r', encoding='utf-8') as f:
        raw = f.read()
        match = re.search(r'(\[.*\])', raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        else:
            raise Exception('Could not find JSON array in audioData.js')

def audible_api_cli(title, author):
    def clean(s):
        return re.sub(r'[^a-zA-Z ]+', '', s)
    query = f'{title} {author}'.strip()
    query = clean(query)
    cli_cmd = [
        'audible', 'api', '/1.0/catalog/products',
        '-p', f'keywords={query}',
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
        return product_list
    except Exception as e:
        return {'error': str(e)}

def main():
    items = load_audio_items()
    dump = []
    for idx, item in enumerate(items):
        old = item.get('old', {})
        title = old.get('title', '')
        author = old.get('author', '')
        print(f'[{idx+1}/{len(items)}] {title} - {author}')
        meta_list = audible_api_cli(title, author)
        dump.append({
            'title': title,
            'author': author,
            'audible_results': meta_list
        })
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dump, f, indent=2, ensure_ascii=False)
    print(f'Wrote Audible metadata dump to {OUTPUT_PATH}')

if __name__ == '__main__':
    main()
