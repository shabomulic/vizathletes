from bs4 import BeautifulSoup

def clean_text(text):
    return " ".join(text.split())

with open('debug_boxscore.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

tables = soup.find_all('table')
for t in tables:
    cap = t.find('caption')
    if cap and 'canisius' in cap.get_text().lower():
        rows = t.find_all('tr')
        if rows:
            headers = [clean_text(c.get_text()) for c in rows[0].find_all(['th', 'td'])]
            print(f"Headers: {headers}")
            # print first data row to see value format
            if len(rows) > 1:
                data = [clean_text(c.get_text()) for c in rows[1].find_all(['td', 'th'])]
                print(f"Row 1: {data}")
        break
