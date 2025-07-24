#!/usr/bin/env python3

import requests
import json

# Test the manual search endpoint
uuid = "03d66986-7035-408c-8835-0b348c2e28e7"  # Example UUID
query = "Mark of the Fool"

try:
    response = requests.post(
        f"http://localhost:4000/api/audiobooks/{uuid}/manual-search",
        headers={"Content-Type": "application/json"},
        json={"query": query}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Manual search successful!")
        print(f"Found {len(data.get('audible_suggestions', []))} suggestions")
        print(f"Selected ID: {data.get('selected_audible_id')}")
        if data.get('audible_suggestions'):
            first = data['audible_suggestions'][0]
            print(f"First result: {first.get('title')} by {first.get('author')}")
    else:
        print(f"Request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"Error testing manual search: {e}")
