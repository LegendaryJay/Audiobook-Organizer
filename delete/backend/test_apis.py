import requests
import json

# Test Open Library directly
url = 'https://openlibrary.org/search.json?q=title:"The Gathering Storm" author:"Robert Jordan"&limit=5'
response = requests.get(url)
data = response.json()

print('Total docs:', data.get('numFound', 0))
if data.get('docs'):
    for i, doc in enumerate(data['docs'][:2]):
        print(f'\n--- Result {i+1} ---')
        print('Title:', doc.get('title', 'N/A'))
        print('Author:', doc.get('author_name', 'N/A'))
        print('Series:', doc.get('series', 'N/A'))
        print('Subject:', doc.get('subject', [])[:10] if doc.get('subject') else 'N/A')
        print('First publish year:', doc.get('first_publish_year', 'N/A'))
        print('Key:', doc.get('key', 'N/A'))

print('\n--- Testing Google Books ---')
import urllib.parse
query = urllib.parse.quote('intitle:"The Gathering Storm" inauthor:"Robert Jordan"')
gb_url = f'https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=3'
print('URL:', gb_url)

gb_response = requests.get(gb_url)
gb_data = gb_response.json()

if gb_data.get('items'):
    for i, item in enumerate(gb_data['items'][:2]):
        vi = item.get('volumeInfo', {})
        print(f'\n--- GB Result {i+1} ---')
        print('Title:', vi.get('title', 'N/A'))
        print('Authors:', vi.get('authors', 'N/A'))
        print('Description:', vi.get('description', 'N/A')[:200] + '...' if vi.get('description') else 'N/A')
        print('Categories:', vi.get('categories', 'N/A'))
