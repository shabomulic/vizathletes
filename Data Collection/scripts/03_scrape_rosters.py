import os
import json
import requests
from bs4 import BeautifulSoup
import time

def load_teams(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_urls(txt_path):
    urls = {}
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ' - ' in line:
                name, url = line.split(' - ', 1)
                urls[name.strip()] = url.strip()
    return urls

def clean_text(text):
    if not text:
        return ""
    # Normalize whitespace
    text = " ".join(text.split())
    # Remove common prefixes found in this specific site format
    prefixes = ['No.:', 'Pos.:', 'Cl.:', 'Ht.:', 'Wt.:']
    for p in prefixes:
        if text.startswith(p):
            text = text[len(p):].strip()
    return text

def find_roster_table(soup):
    tables = soup.find_all('table')
    for table in tables:
        # Check explicit headers
        thead = table.find('thead')
        if thead:
            header_text = thead.get_text().lower()
            if ('no.' in header_text or '#' in header_text) and 'name' in header_text:
                return table
        
        # Check first row if no thead or as fallback
        first_row = table.find('tr')
        if first_row:
            row_text = first_row.get_text().lower()
            # Strict check for header-like row
            if ('no.' in row_text or '#' in row_text) and 'name' in row_text:
                return table
    
    # Fallback to the first table if reasonable
    if tables:
        return tables[0]
    return None

def scrape_roster(url):
    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        table = find_roster_table(soup)
        if not table:
            print(f"No table found for {url}")
            return []

        players = []
        
        # Try to identify columns from headers
        headers_map = {}
        # ... logic to map headers ...
        # We need to re-find the header row within this specific table
        rows = table.find_all('tr')
        
        # Determine header row using the same logic as table finder
        header_row = None
        start_row_idx = 0
        
        # Try finding thead first
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
        else:
            # Look for the row with 'Name'
            for idx, r in enumerate(rows):
                txt = r.get_text().lower()
                if 'name' in txt and ('no' in txt or '#' in txt):
                    header_row = r
                    start_row_idx = idx + 1
                    break
        
        if header_row:
            cols = header_row.find_all(['th', 'td'])
            for idx, col in enumerate(cols):
                text = clean_text(col.get_text()).lower()
                if 'no' in text or '#' in text:
                    headers_map['number'] = idx
                elif 'name' in text:
                    headers_map['name'] = idx
                elif 'pos' in text:
                    headers_map['position'] = idx
                elif 'cl' in text or 'yr' in text:
                    headers_map['class'] = idx
                elif 'ht' in text:
                    headers_map['height'] = idx
                elif 'wt' in text:
                    headers_map['weight'] = idx
        else:
             print("Could not identify header row.")
             return []

        # Iterate over data rows
        # If we used thead, start_row_idx is 0 (relative to tbody) or we used find_all('tr') on table.
        # Let's iterate all rows and skip the header row.
        
        for row in rows:
            if row == header_row:
                continue
                
            cols = row.find_all(['td', 'th'])
            if not cols:
                continue
            
            player = {}
            
            # Helper to safely get index
            def get_col(idx_name):
                idx = headers_map.get(idx_name)
                if idx is not None and idx < len(cols):
                    return clean_text(cols[idx].get_text())
                return None

            # If we mapped headers, use them
            if headers_map:
                player['number'] = get_col('number')
                player['name'] = get_col('name')
                player['position'] = get_col('position')
                player['class_year'] = get_col('class')
                player['height'] = get_col('height')
                player['weight'] = get_col('weight')
            else:
                continue

            # Basic Validation: Must have a name and not be a repeat of header
            if player.get('name') and 'name' not in player['name'].lower():
                 players.append(player)

        return players

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    teams_path = os.path.join(base_dir, 'teams.json')
    urls_path = os.path.join(base_dir, 'Top 25 URLs.txt')
    data_dir = os.path.join(base_dir, 'data')

    teams = load_teams(teams_path)
    urls = parse_urls(urls_path)
    
    # Map name to (slug, division)
    name_to_info = {t['name']: (t['slug'], t['division']) for t in teams}
    
    # Division folder mapping
    div_map = {
        'DI': 'Division I',
        'DII': 'Division II',
        'DIII': 'Division III'
    }

    # Manual Name Fixes
    name_fixes = {
        "Bryant and Stratton College": ("bryantandstrattoncollegewi", "DII"),
        "Montgomery County Community College (PA)": ("montgomerycountycommunitycollege", "DIII"),
        "UCNJ": ("ucnj", "DIII"),
        "Butler Community College - KS": ("butlercommunitycollegeks", "DI"),
        "Riverland Community College": ("riverlandcommunitycollege", "DIII"),
        "Northern Essex Community College": ("northernessexcommunitycollege", "DIII"),
        "Sandhills Community College": ("sandhillscommunitycollege", "DIII"),
        "Massasoit Community College": ("massasoitcommunitycollege", "DIII"),
        "North Country Community College": ("northcountrycommunitycollege", "DIII")
    }

    for school_name, url in urls.items():
        info = name_to_info.get(school_name)
        
        # Try fixes if not found
        if not info:
            if school_name in name_fixes:
                info = name_fixes[school_name]
        
        if not info:
            print(f"SKIPPING: Could not find info for {school_name}")
            continue

        slug, div_code = info
        div_folder = div_map.get(div_code, div_code)

        print(f"Scraping {school_name} ({div_code})...")
        roster_data = scrape_roster(url)
        
        if roster_data:
            school_dir = os.path.join(data_dir, div_folder, slug)
            os.makedirs(school_dir, exist_ok=True)
            output_path = os.path.join(school_dir, 'roster.json')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(roster_data, f, indent=4)
            print(f"  Saved {len(roster_data)} players to {output_path}")
        else:
            print(f"  WARNING: No roster data found for {school_name}")
        
        # Be polite
        time.sleep(1) # Reduced sleep a bit for efficiency since we have 65 teams

if __name__ == "__main__":
    main()
