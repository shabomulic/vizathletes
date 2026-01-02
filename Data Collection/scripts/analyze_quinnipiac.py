from bs4 import BeautifulSoup
import re

def clean_text(text):
    if not text: return ""
    return " ".join(text.split())

def clean_position(pos_text):
    match = re.match(r'^([A-Za-z]+(?:\/[A-Za-z]+)?)', pos_text)
    if match: return match.group(1)
    return pos_text.split()[0] if pos_text else "N/A"

with open('debug_quinnipiac_roster.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

print("Analyzing Table...")
table = soup.find('table')
if table:
    headers_map = {}
    thead = table.find('thead')
    header_row = thead.find('tr') if thead else table.find('tr')
    
    if header_row:
        cols = header_row.find_all(['th', 'td'])
        print(f"Header Row Cols: {len(cols)}")
        for idx, col in enumerate(cols):
            text = clean_text(col.get_text()).lower()
            print(f"  {idx}: {text}")
            if 'no' in text or '#' in text: headers_map['number'] = idx
            elif 'name' in text: headers_map['name'] = idx
            elif 'pos' in text: headers_map['position'] = idx
            elif 'cl' in text or 'yr' in text: headers_map['class_year'] = idx
            elif 'ht' in text: headers_map['height'] = idx
            elif 'wt' in text: headers_map['weight'] = idx
    
    print(f"Map: {headers_map}")

    tbody = table.find('tbody')
    rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
    
    for i, row in enumerate(rows):
        cols = row.find_all(['td', 'th'])
        if not cols: continue
        print(f"Row {i} Cols: {len(cols)}")
        
        player = {}
        for k, idx in headers_map.items():
            # THIS IS THE SUSPECT AREA
            if idx < len(cols):
                player[k] = clean_text(cols[idx].get_text())
            else:
                print(f"  WARNING: Map index {idx} ({k}) out of bounds for row len {len(cols)}")
        
        if 'name' in headers_map:
             # Logic from script:
             cell = cols[headers_map['name']] # <--- CRASH potential if idx >= len(cols)
             a = cell.find('a')
             if a: player['name'] = clean_text(a.get_text())
else:
    print("No table found.")
