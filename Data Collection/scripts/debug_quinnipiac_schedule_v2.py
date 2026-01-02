import requests

url = "https://gobobcats.com/sports/mens-basketball/schedule/2025-26"
headers = {'User-Agent': 'Mozilla/5.0'}
try:
    response = requests.get(url, headers=headers)
    with open('debug_quinnipiac_schedule_v2.html', 'wb') as f:
        f.write(response.content)
    print("Saved schedule v2.")
except Exception as e:
    print(f"Failed: {e}")
