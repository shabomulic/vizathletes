import requests

def save_html(url, filename):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved to {filename}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    save_html("https://gogriffs.com/sports/mens-basketball/roster?view=2", "debug_roster.html")
    save_html("https://gogriffs.com/sports/mens-basketball/stats/2024-25/no-10-9-arizona/boxscore/9192", "debug_boxscore.html")
