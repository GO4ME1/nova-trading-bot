import requests
import base64
import json

# Read the new file content
with open('/home/ubuntu/nova-fixed/app.py', 'r') as f:
    new_content = f.read()

# Encode to base64
content_encoded = base64.b64encode(new_content.encode()).decode()

# Get current file SHA
repo_url = "https://api.github.com/repos/GO4ME1/nova-trading-bot/contents/src/main_dex_fixed.py"

print("Getting current file SHA...")
response = requests.get(repo_url)
if response.status_code == 200:
    current_file = response.json()
    sha = current_file['sha']
    print(f"Current SHA: {sha}")
    
    # Prepare update payload
    payload = {
        "message": "Fix: Switch to DexScreener API and Jupiter Ultra Swap API\n\n- Replace Birdeye REST API with DexScreener API for token discovery\n- Update to Jupiter Ultra Swap API (current production endpoints)\n- Add comprehensive logging with visual indicators\n- Improve safety scoring algorithm\n- Add multiple token source fallbacks",
        "content": content_encoded,
        "sha": sha
    }
    
    print("\nTo update the file, you need a GitHub Personal Access Token.")
    print("Please provide your token or use the web interface instead.")
    print("\nAlternatively, the commit is ready in the local repo.")
    print("You can push it manually with: cd /home/ubuntu/nova-trading-bot-repo && git push")
else:
    print(f"Error getting file: {response.status_code}")
    print(response.text)

