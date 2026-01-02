import requests

url = "https://gobobcats.com/sports/mens-basketball/roster?view=2"
headers = {'User-Agent': 'Mozilla/5.0'}
try:
    response = requests.get(url, headers=headers)
    with open('debug_quinnipiac_roster.html', 'wb') as f:
        f.write(response.content)
    print("Saved debug_quinnipiac_roster.html")
except Exception as e:
    print(f"Failed: {e}")
