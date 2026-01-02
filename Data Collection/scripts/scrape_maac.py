import os
import json
import requests
import time
import re
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

# Configuration will be initialized in main() based on conference
DATA_DIR = None
ROSTERS_FILE = None
SCHEDULES_FILE = None
ERROR_LOG_FILE = None
CONF_NAME = None

def log_error(team_name, url, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [{team_name}] {url}: {message}\n")
    print(f"ERROR: {message}")

def sanitize_team_folder(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def sanitize_filename(name):
    return re.sub(r'[^\w\s\-\_]', '', name).strip()

def clean_text(text):
    if not text: return ""
    return " ".join(text.split())

def load_urls(file_path):
    team_urls = {}
    if not os.path.exists(file_path): return team_urls
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ' - ' in line:
                name, url = line.strip().split(' - ', 1)
                team_urls[name.strip()] = url.strip()
    return team_urls

def extract_name_parts(name):
    clean = re.sub(r'[^\w\s]', '', name.lower())
    return set(clean.split())

def match_player_folder(box_score_name, players_map):
    box_parts = extract_name_parts(box_score_name)
    for roster_tuple, folder_name in players_map.items():
        roster_parts = set(roster_tuple)
        if roster_parts == box_parts: return folder_name
        if roster_parts.issubset(box_parts) and len(roster_parts) > 0: return folder_name
        if box_parts.issubset(roster_parts) and len(box_parts) > 1: return folder_name
    return None

def clean_position(pos_text):
    """Clean position text. e.g. 'Guard G 6\'4" 190 lbs' -> 'Guard'"""
    match = re.match(r'^([A-Za-z]+(?:\/[A-Za-z]+)?)', pos_text)
    if match: return match.group(1)
    return pos_text.split()[0] if pos_text else "N/A"

def scrape_roster(team_name, url):
    print(f"  Scraping roster for {team_name}...")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        players = []
        
        # Table
        table = soup.find('table')
        if table:
            headers_map = {}
            thead = table.find('thead')
            header_row = thead.find('tr') if thead else table.find('tr')
            if header_row:
                for idx, col in enumerate(header_row.find_all(['th', 'td'])):
                    text = clean_text(col.get_text()).lower()
                    if 'no' in text or '#' in text: headers_map['number'] = idx
                    elif 'name' in text: headers_map['name'] = idx
                    elif 'pos' in text: headers_map['position'] = idx
                    elif 'cl' in text or 'yr' in text: headers_map['class_year'] = idx
                    elif 'ht' in text: headers_map['height'] = idx
                    elif 'wt' in text: headers_map['weight'] = idx
            
            tbody = table.find('tbody')
            rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if not cols: continue
                player = {}
                for k, i in headers_map.items():
                    if i < len(cols): player[k] = clean_text(cols[i].get_text())
                
                if 'name' in headers_map and headers_map['name'] < len(cols):
                    cell = cols[headers_map['name']]
                    a = cell.find('a')
                    if a: player['name'] = clean_text(a.get_text())
                
                if player.get('name'):
                    if 'position' in player: player['position'] = clean_position(player['position'])
                    players.append(player)

        # Cards
        if not players:
            cards = soup.select('li.sidearm-roster-player') or soup.select('.roster-player')
            for card in cards:
                player = {}
                name_elem = card.select_one('.sidearm-roster-player-name h3 a') or card.select_one('.sidearm-roster-player-name')
                if name_elem:
                    player['name'] = re.sub(r'^\d+\s+', '', clean_text(name_elem.get_text()))
                    pos = card.select_one('.sidearm-roster-player-position')
                    if pos: player['position'] = clean_position(clean_text(pos.get_text()))
                    
                    num = card.select_one('.sidearm-roster-player-jersey-number')
                    if num: player['number'] = clean_text(num.get_text())
                    ht = card.select_one('.sidearm-roster-player-height')
                    if ht: player['height'] = clean_text(ht.get_text())
                    wt = card.select_one('.sidearm-roster-player-weight')
                    if wt: player['weight'] = clean_text(wt.get_text())
                    yr = card.select_one('.sidearm-roster-player-academic-year')
                    if yr: player['class_year'] = clean_text(yr.get_text())
                    players.append(player)

        if players:
            team_folder = sanitize_team_folder(team_name)
            team_dir = os.path.join(DATA_DIR, team_folder)
            os.makedirs(team_dir, exist_ok=True)
            
            # Pre-create player folders
            p_dir_base = os.path.join(team_dir, 'players')
            os.makedirs(p_dir_base, exist_ok=True)
            for p in players:
                p_folder = sanitize_filename(p['name'])
                os.makedirs(os.path.join(p_dir_base, p_folder), exist_ok=True)

            with open(os.path.join(team_dir, 'roster.json'), 'w', encoding='utf-8') as f:
                json.dump(players, f, indent=4)
            return players
        return []
    except Exception as e:
        log_error(team_name, url, f"Roster scrape failed: {e}")
        return []

def calculate_advanced_stats(basic_stats):
    s = {}
    def get_split(key):
        val = basic_stats.get(key, '0-0')
        if '-' in val:
            try: return float(val.split('-')[0]), float(val.split('-')[1])
            except: return 0.0, 0.0
        return 0.0, 0.0

    fgm, fga = get_split('FGM-A')
    fg3m, fg3a = get_split('3PM-A')
    ftm, fta = get_split('FTM-A')
    
    s['fgm'] = str(int(fgm))
    s['fga'] = str(int(fga))
    s['fgm3'] = str(int(fg3m))
    s['fga3'] = str(int(fg3a))
    s['ftm'] = str(int(ftm))
    s['fta'] = str(int(fta))
    s['pts'] = basic_stats.get('TP', '0')
    s['oreb'] = basic_stats.get('OREB', '0')
    s['dreb'] = basic_stats.get('DREB', '0')
    s['treb'] = basic_stats.get('REB', '0')
    s['ast'] = basic_stats.get('AST', '0')
    s['stl'] = basic_stats.get('STL', '0')
    s['blk'] = basic_stats.get('BLK', '0')
    s['to'] = basic_stats.get('TO', '0')
    s['pf'] = basic_stats.get('PF', '0')
    s['min'] = basic_stats.get('MIN', '0')
    
    s['fgpt'] = f"{(fgm/fga*100):.1f}" if fga else "0.0"
    s['fgpt3'] = f"{(fg3m/fg3a*100):.1f}" if fg3a else "0.0"
    s['ftpt'] = f"{(ftm/fta*100):.1f}" if fta else "0.0"
    
    # Per Game/Minute placeholders to mimic schema
    # Since single game file, Per Game matches Game value
    s['fgppg'] = s['fgpt'] 
    s['fgmpg'] = f"{fgm:.1f}"
    s['fgapg'] = f"{fga:.1f}"
    s['ptspg'] = f"{float(s['pts']):.1f}"
    
    # Defaults for opp/eff/tposs/etc.
    s['tposs'] = "0.000"
    s['qp'] = "0.0"
    
    return s

def scrape_box_score(game_url, team_name, team_dir, game_date, players_map):
    print(f"    Scraping box score: {game_url}")
    try:
        response = requests.get(game_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        normalized_team = clean_text(team_name).lower()
        team_parts = [p for p in normalized_team.split() if len(p) > 2]
        tables = soup.find_all('table')
        my_team_table = None
        headers_map = {}
        
        for table in tables:
            rows = table.find_all('tr')
            if not rows: continue
            
            # Identify headers and map them
            header_row = table.find('thead')
            if not header_row: header_row = rows[0]
            ths = header_row.find_all(['th', 'td'])
            th_texts = [clean_text(th.get_text()).upper() for th in ths]
            
            temp_map = {}
            for idx, txt in enumerate(th_texts):
                if 'PLAYER' in txt: temp_map['Player Name'] = idx
                elif 'MIN' in txt: temp_map['MIN'] = idx
                elif 'FG' in txt: temp_map['FGM-A'] = idx
                elif '3P' in txt: temp_map['3PM-A'] = idx
                elif 'FT' in txt: temp_map['FTM-A'] = idx
                elif 'ORB-DRB' in txt: temp_map['ORB-DRB'] = idx
                elif 'OFF' in txt or 'OREB' in txt: temp_map['OREB'] = idx
                elif 'DEF' in txt or 'DREB' in txt: temp_map['DREB'] = idx
                elif 'TOT' in txt or 'REB' in txt: temp_map['REB'] = idx
                elif 'A' == txt or 'AST' in txt: temp_map['AST'] = idx
                elif 'STL' in txt: temp_map['STL'] = idx
                elif 'BLK' in txt: temp_map['BLK'] = idx
                elif 'TO' in txt: temp_map['TO'] = idx
                elif 'PF' in txt: temp_map['PF'] = idx
                elif 'PTS' in txt or 'TP' in txt: temp_map['TP'] = idx

            # Must have at least MIN and TP to be a stats table
            if not ('MIN' in temp_map and 'TP' in temp_map):
                continue
            
            # Check if this is OUR team
            is_ours = False
            caption = table.find('caption')
            if caption:
                cap_text = clean_text(caption.get_text()).lower()
                for part in team_parts:
                    if part in cap_text:
                        is_ours = True
                        break
            
            if not is_ours and 'Player Name' in temp_map:
                p_idx = temp_map['Player Name']
                for r in rows[1:8]: # Check more rows if needed
                    cells = r.find_all(['td', 'th'])
                    if p_idx < len(cells):
                        p_name = clean_text(cells[p_idx].get_text())
                        # Skip total/header rows if they repeat
                        if p_name.upper() in ['PLAYER', 'TM', 'TOTALS', 'TEAM', 'TM TEAM']: continue
                        p_parts = extract_name_parts(p_name)
                        for roster_tuple in players_map.keys():
                            roster_parts = set(roster_tuple)
                            if roster_parts == p_parts or (roster_parts.issubset(p_parts) and len(p_parts) > 0 and len(roster_parts) > 0):
                                is_ours = True
                                break
                    if is_ours: break
            
            if is_ours:
                my_team_table = table
                headers_map = temp_map
                break
        
        if not my_team_table: return

        team_basic_stats = {}
        player_stats = []
        rows = my_team_table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 2: continue
            
            c0 = clean_text(cols[0].get_text()).lower()
            c1 = clean_text(cols[1].get_text()).lower()
            if 'total' in c0 or 'team' in c0 or 'total' in c1:
                for k, i in headers_map.items():
                    if i < len(cols): team_basic_stats[k] = clean_text(cols[i].get_text())
                
                # Split ORB-DRB if present
                if 'ORB-DRB' in team_basic_stats:
                     odb = team_basic_stats['ORB-DRB']
                     if '-' in odb:
                         parts = odb.split('-')
                         if len(parts) >= 2:
                             team_basic_stats['OREB'] = parts[0]
                             team_basic_stats['DREB'] = parts[1]
                continue
            
            if 'Player Name' in headers_map and headers_map['Player Name'] < len(cols):
                p_name = clean_text(cols[headers_map['Player Name']].get_text())
                p_name = re.sub(r'^\d+\s+', '', p_name)
                if p_name.upper() not in ['TM', 'TEAM', 'TM TEAM', 'TOTALS', 'PLAYER']:
                    p_data = {'Player Name': p_name, 'eventDateFormatted': game_date}
                    for k, i in headers_map.items():
                        if k != 'Player Name' and i < len(cols): 
                            p_data[k] = clean_text(cols[i].get_text())
                    
                    # Split ORB-DRB if present
                    if 'ORB-DRB' in p_data:
                        odb = p_data['ORB-DRB']
                        if '-' in odb:
                            parts = odb.split('-')
                            if len(parts) >= 2:
                                p_data['OREB'] = parts[0]
                                p_data['DREB'] = parts[1]
                                # remove combined key if undesired? Keep separate
                    
                    player_stats.append(p_data)

        if team_basic_stats:
            extended_stats = calculate_advanced_stats(team_basic_stats)
            final_obj = {
                "stats": extended_stats,
                "eventDateFormatted": game_date,
                "boxScoreLink": game_url.split('/')[-1] + ".xml",
                "event": {
                    "teams": [{"name": team_name, "result": extended_stats.get('pts'), "winner": False}],
                    "status": "Final",
                    "sport": "Basketball"
                }
            }
            ts_dir = os.path.join(team_dir, 'team')
            os.makedirs(ts_dir, exist_ok=True)
            with open(os.path.join(ts_dir, f"{sanitize_filename(game_date)}.json"), 'w', encoding='utf-8') as f:
                json.dump(final_obj, f, indent=4)

        p_dir_base = os.path.join(team_dir, 'players')
        os.makedirs(p_dir_base, exist_ok=True)
        for p in player_stats:
            folder_name = match_player_folder(p['Player Name'], players_map)
            if not folder_name:
                if ',' in p['Player Name']:
                    parts = p['Player Name'].split(',')
                    if len(parts) == 2: folder_name = f"{parts[1].strip()} {parts[0].strip()}"
                else: folder_name = sanitize_filename(p['Player Name'])
            
            p_folder = sanitize_filename(folder_name)
            if len(p_folder) < 2: continue
            target_dir = os.path.join(p_dir_base, p_folder)
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, f"{sanitize_filename(game_date)}_{p_folder}.json"), 'w', encoding='utf-8') as f:
                json.dump(p, f, indent=4)

    except Exception as e:
        log_error(team_name, game_url, f"Box scrape error: {e}")

def process_season_stats(team_name, team_dir):
    print(f"  Calculating season stats for {team_name}...")
    players_dir = os.path.join(team_dir, 'players')
    if not os.path.exists(players_dir): return
    
    for p_folder in os.listdir(players_dir):
        p_path = os.path.join(players_dir, p_folder)
        if not os.path.isdir(p_path): continue
        
        totals = {k:0 for k in ['min','fgm','fga','3pm','3pa','ftm','fta','oreb','dreb','reb','ast','stl','blk','to','pf','pts']}
        games = 0
        
        for fname in os.listdir(p_path):
            if fname.endswith('.json') and '_season.json' not in fname:
                try:
                    with open(os.path.join(p_path, fname), 'r') as f: d = json.load(f)
                    games += 1
                    
                    def p_int(v): 
                        try: return int(v) 
                        except: return 0
                    def p_split(v):
                        try: return map(int, v.split('-'))
                        except: return 0,0
                    
                    totals['min'] += p_int(str(d.get('MIN','0')).split(':')[0])
                    m,a = p_split(d.get('FGM-A','0-0')); totals['fgm']+=m; totals['fga']+=a
                    m,a = p_split(d.get('3PM-A','0-0')); totals['3pm']+=m; totals['3pa']+=a
                    m,a = p_split(d.get('FTM-A','0-0')); totals['ftm']+=m; totals['fta']+=a
                    totals['oreb']+=p_int(d.get('OREB','0'))
                    totals['dreb']+=p_int(d.get('DREB','0'))
                    totals['reb']+=p_int(d.get('REB','0'))
                    totals['ast']+=p_int(d.get('AST','0'))
                    totals['stl']+=p_int(d.get('STL','0'))
                    totals['blk']+=p_int(d.get('BLK','0'))
                    totals['to']+=p_int(d.get('TO','0'))
                    totals['pf']+=p_int(d.get('PF','0'))
                    totals['pts']+=p_int(d.get('TP','0'))
                except: pass
        
        if games > 0:
            season = {
                'games_played': games, 'MIN': totals['min'],
                'FGM': totals['fgm'], 'FGA': totals['fga'],
                '3PM': totals['3pm'], '3PA': totals['3pa'],
                'FTM': totals['ftm'], 'FTA': totals['fta'],
                'OREB': totals['oreb'], 'DREB': totals['dreb'], 'REB': totals['reb'],
                'AST': totals['ast'], 'STL': totals['stl'], 'BLK': totals['blk'],
                'TO': totals['to'], 'PF': totals['pf'], 'PTS': totals['pts']
            }
            with open(os.path.join(p_path, f"{sanitize_filename(p_folder)}_season.json"), 'w') as f:
                json.dump(season, f, indent=4)

def scrape_schedule(team_name, url, team_dir, players_map):
    print(f"  Scraping schedule for {team_name}...")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try modern Sidearm NextGen/Standard containers first
        container = soup.find(id='listPanel') or soup.find(class_='c-schedulepage__games')
        if container:
            game_cards = container.select('.schedule-game, .game-card, .s-game-card, .sidearm-schedule-game')
        else:
            game_cards = soup.select('.schedule-game, .game-card, .s-game-card, .sidearm-schedule-game')
            
        if not game_cards:
            tbody = soup.find('tbody')
            if tbody: game_cards = tbody.find_all('tr')
            
        today = datetime.now()
        
        for card in game_cards:
            game_date_str = "Unknown"
            # Look for date with fallbacks
            date_elem = card.find(class_=re.compile(r'date|day'))
            if not date_elem:
                date_elem = card.find(attrs={"data-test-id": re.compile(r'date|day')})
            
            if date_elem:
                raw_date = clean_text(date_elem.get_text())
                game_date_str = raw_date
            elif card.name == 'tr':
                cols = card.find_all('td')
                if cols: game_date_str = clean_text(cols[0].get_text())

            try:
                clean_dt = re.sub(r'\s*\(.*?\)', '', game_date_str).strip()
                dt_obj = None
                for fmt in ["%B %d, %Y", "%b %d", "%B %d"]:
                    try:
                        dt_obj = datetime.strptime(clean_dt, fmt)
                        if dt_obj.year == 1900:
                            if dt_obj.month >= 10: dt_obj = dt_obj.replace(year=2025)
                            else: dt_obj = dt_obj.replace(year=2026)
                        break
                    except: pass
                
                if dt_obj:
                    if dt_obj.date() > today.date(): continue
                    game_date_str = dt_obj.strftime("%b %d").replace(" 0", " ")
            except: pass
            
            box_link = None
            links = card.find_all('a')
            for link in links:
                if 'box' in link.get_text().lower() or 'boxscore' in link.get('href', '').lower():
                    box_link = urljoin(url, link.get('href'))
                    break
            
            if box_link:
                scrape_box_score(box_link, team_name, team_dir, game_date_str, players_map)
                time.sleep(1)

    except Exception as e:
        log_error(team_name, url, f"Schedule scrape failed: {e}")

def main():
    global DATA_DIR, ROSTERS_FILE, SCHEDULES_FILE, ERROR_LOG_FILE, CONF_NAME
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--conference', '-c', default='MAAC', help='Conference name (e.g., MAAC, NEC)')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    
    CONF_NAME = args.conference.upper()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(base_dir, 'data', f'{CONF_NAME} Teams')
    ROSTERS_FILE = os.path.join(base_dir, f'{CONF_NAME} Rosters.txt')
    SCHEDULES_FILE = os.path.join(base_dir, f'{CONF_NAME} Schedules.txt')
    ERROR_LOG_FILE = os.path.join(base_dir, 'logs', f'{CONF_NAME.lower()}_scraper_errors.txt')
    
    os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print(f"Starting scrape for {CONF_NAME}...")
    
    roster_urls = load_urls(ROSTERS_FILE)
    schedule_urls = load_urls(SCHEDULES_FILE)
    
    if not roster_urls:
        print(f"No rosters found at {ROSTERS_FILE}")
        return

    count = 0
    for team, r_url in roster_urls.items():
        if args.limit and count >= args.limit: break
        
        team_folder = sanitize_team_folder(team)
        team_dir = os.path.join(DATA_DIR, team_folder)
        
        roster = scrape_roster(team, r_url)
        p_map = {}
        for p in roster:
            parts = tuple(sorted(extract_name_parts(p['name'])))
            p_map[parts] = sanitize_filename(p['name'])
            
        s_url = schedule_urls.get(team)
        if s_url:
            scrape_schedule(team, s_url, team_dir, p_map)
            process_season_stats(team, team_dir)
        
        count += 1
        time.sleep(2)

if __name__ == "__main__":
    main()
