import requests
import urllib3
import re

urllib3.disable_warnings()

# The main bundle references chunk files — let's search inside it
r = requests.get('https://deckbuilder.egmanevents.com/static/js/main.7dee16bf.js', verify=False, timeout=30)
js = r.text

# Find chunk references
chunks = re.findall(r'"([0-9a-f]{8,})"', js)
chunk_ids = list(set(chunks))[:20]
print("Possible chunk hashes:", chunk_ids[:10])

# Look for the pattern used to load chunks
chunk_patterns = re.findall(r'static/[^"\']{3,60}\.js', js)
print("\nChunk URL patterns:")
for p in set(chunk_patterns):
    print("  /{}".format(p))

# Search for the key near any "key", "anon", "service" strings
for kw in ['anon', 'service_role', 'ANON_KEY', 'apiKey', '"key"']:
    idx = js.find(kw)
    if idx >= 0:
        print("\nFound '{}' at {}:".format(kw, idx))
        print(js[max(0,idx-30):idx+150])
