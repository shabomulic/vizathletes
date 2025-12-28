"""
02_scrape_stats.py

Scrapes game and player statistics for all teams in teams.json.
Supports Division I, II, and III with division-specific API endpoints.
"""

import requests
import json
import os
import time
import re
import argparse
from bs4 import BeautifulSoup

# Division to URL path mapping
DIVISION_PATHS = {
    'DI': 'div1',
    'DII': 'div2',
    'DIII': 'div3'
}

DIVISION_FOLDERS = {
    'DI': 'Division I',
    'DII': 'Division II',
    'DIII': 'Division III'
}


def sanitize_filename(name):
    safe = re.sub(r'[\\/*?:"<>|]', "", name)
    return safe.strip()


def scrape_box_score(url, target_team_name):
    print(f"    Fetching box score: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            print(f"    Failed to fetch box score: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        captions = soup.find_all("div", class_="caption")
        target_table = None
        
        norm_target = target_team_name.lower().replace(" ", "")
        
        for cap in captions:
            cap_text = cap.get_text().lower().replace(" ", "")
            if norm_target in cap_text:
                parent = cap.parent
                fullbox = parent.find("div", class_="monostats-fullbox")
                if fullbox:
                    target_table = fullbox.find("table")
                break
        
        if not target_table:
            print(f"    Could not find table for {target_team_name}")
            return []

        player_stats = []
        rows = target_table.find_all("tr")
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 16:
                continue
            
            raw_name = cells[1].get_text().strip()
            name = raw_name.rstrip(".").strip()
            
            if name.lower() in ["team", "totals"]:
                continue
                
            stats = {
                "Player Name": name,
                "FGM-A": cells[3].get_text().strip(),
                "3PM-A": cells[4].get_text().strip(),
                "FTM-A": cells[5].get_text().strip(),
                "OREB": cells[6].get_text().strip(),
                "DREB": cells[7].get_text().strip(),
                "REB": cells[8].get_text().strip(),
                "PF": cells[9].get_text().strip(),
                "TP": cells[10].get_text().strip(),
                "AST": cells[11].get_text().strip(),
                "TO": cells[12].get_text().strip(),
                "BLK": cells[13].get_text().strip(),
                "STL": cells[14].get_text().strip(),
                "MIN": cells[15].get_text().strip()
            }
            player_stats.append(stats)
            
        return player_stats

    except Exception as e:
        print(f"    Error scraping box score: {e}")
        return []


def scrape_stats(target_division=None):
    # Paths - script is now in scripts/ folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    teams_path = os.path.join(base_dir, 'teams.json')
    data_dir = os.path.join(base_dir, 'data')
    
    # Load teams
    try:
        with open(teams_path, 'r') as f:
            teams = json.load(f)
    except FileNotFoundError:
        print("Error: teams.json not found. Run 01_scrape_teams.py first.")
        return

    # Filter by division if specified
    if target_division:
        teams = [t for t in teams if t.get('division') == target_division]
        print(f"Filtered to {len(teams)} teams in {target_division}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"Starting stats scrape for {len(teams)} teams...")

    for i, team in enumerate(teams):
        slug = team['slug']
        name = team['name']
        division = team.get('division', 'DII')
        
        div_path = DIVISION_PATHS.get(division, 'div2')
        div_folder = DIVISION_FOLDERS.get(division, 'Division II')
        
        # URL format with division-specific path
        url = f"https://njcaastats.prestosports.com/sports/mbkb/2025-26/{div_path}/teams/{slug}?tmpl=teaminfo-network-monospace-json-template"
        
        print(f"[{i+1}/{len(teams)}] [{division}] {name} ({slug})...")
        
        # Create team directory under the correct division folder
        team_dir = os.path.join(data_dir, div_folder, slug)
        os.makedirs(team_dir, exist_ok=True)
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 404:
                print(f"  WARNING: 404 Not Found for {slug}")
                continue
            response.raise_for_status()
            
            team_match = re.search(r'(https://[^"]+/teamData/[^"]+\.json)', response.text)
            players_match = re.search(r'(https://[^"]+/playersData/[^"]+\.json)', response.text)
            
            # --- PROCESS TEAM DATA ---
            team_data_list = []
            my_team_id = None
            
            if team_match:
                team_json_url = team_match.group(1)
                try:
                    res = requests.get(team_json_url, headers=headers)
                    res.raise_for_status()
                    
                    with open(os.path.join(team_dir, "team.json"), 'w', encoding='utf-8') as f:
                        f.write(res.text)
                    
                    data = res.json()
                    if isinstance(data, dict):
                        if 'events' in data and isinstance(data['events'], list):
                             team_data_list = data['events']
                        else:
                             team_data_list = [v for v in data.values() if isinstance(v, dict)]
                        
                        # New: Check attributes for teamId
                        if not my_team_id and 'attributes' in data and 'teamId' in data['attributes']:
                            my_team_id = data['attributes']['teamId']
                    else:
                        team_data_list = data
                        
                    # Find Team ID from events if not found yet
                    if not my_team_id:
                        for game in team_data_list:
                            if not isinstance(game, dict): continue
                            if 'event' in game and 'teams' in game['event']:
                                for t in game['event']['teams']:
                                    if t.get('name') == name:
                                        my_team_id = t.get('teamId')
                                        break
                                    if t.get('name', '').lower().replace(' ','') == name.lower().replace(' ',''):
                                        my_team_id = t.get('teamId')
                                        break
                            if my_team_id: break
                        
                    if my_team_id:
                        print(f"  Team ID: {my_team_id}")

                    # Save Game JSONs
                    games_dir = os.path.join(team_dir, "team")
                    os.makedirs(games_dir, exist_ok=True)
                    
                    for game in team_data_list:
                        if not isinstance(game, dict): continue
                        
                        date_fmt = game.get('eventDateFormatted', 'Unknown Date')
                        safe_date = sanitize_filename(date_fmt)
                        
                        base_filename = f"{safe_date}.json"
                        counter = 1
                        while os.path.exists(os.path.join(games_dir, base_filename)):
                            base_filename = f"{safe_date}_{counter}.json"
                            counter += 1
                        
                        with open(os.path.join(games_dir, base_filename), 'w', encoding='utf-8') as f:
                            json.dump(game, f, indent=4)
                            
                except Exception as e:
                    print(f"  Error processing team JSON: {e}")

            # --- PROCESS PLAYERS ---
            filtered_players = []
            if players_match:
                players_json_url = players_match.group(1)
                try:
                    res = requests.get(players_json_url, headers=headers)
                    res.raise_for_status()
                    with open(os.path.join(team_dir, "players.json"), 'w', encoding='utf-8') as f:
                        f.write(res.text)
                        
                    p_data = res.json()
                    p_list = []
                    if isinstance(p_data, dict):
                        if 'individuals' in p_data and isinstance(p_data['individuals'], list):
                             p_list = p_data['individuals']
                        else:
                             p_list = [v for v in p_data.values() if isinstance(v, dict)]
                    else:
                        p_list = p_data
                        
                    # Load roster for filtering
                    roster_names = set()
                    roster_path = os.path.join(team_dir, 'roster.json')
                    if os.path.exists(roster_path):
                        try:
                            with open(roster_path, 'r', encoding='utf-8') as rf:
                                r_data = json.load(rf)
                                for rp in r_data:
                                    nm = rp.get('name', '').strip()
                                    if nm: roster_names.add(nm.lower())
                            print(f"  Loaded {len(roster_names)} players from roster.json")
                        except Exception as roster_err:
                            print(f"  Error loading roster: {roster_err}")
                        
                    players_root = os.path.join(team_dir, "players")
                    os.makedirs(players_root, exist_ok=True)
                    
                    count = 0
                    for p in p_list:
                        if not isinstance(p, dict): continue
                        
                        p_team_id = p.get('teamId')
                        p_full_name = p.get('fullName', '').strip().lower()
                        
                        match_by_id = (my_team_id and p_team_id == my_team_id)
                        match_by_roster = (p_full_name in roster_names)
                        
                        # Only proceed if we match by ID OR by roster name
                        if not (match_by_id or match_by_roster):
                            continue
                            
                        full_name = p.get('fullName')
                        first = p.get('firstName')
                        last = p.get('lastName')
                        
                        if full_name:
                            name_str = full_name
                        elif first and last:
                            name_str = f"{first} {last}"
                        else:
                            name_str = f"Player_{p.get('playerId')}"
                            
                        safe_name = sanitize_filename(name_str)
                        
                        p_folder = os.path.join(players_root, safe_name)
                        
                        if os.path.isfile(p_folder):
                            os.remove(p_folder)
                            
                        os.makedirs(p_folder, exist_ok=True)
                        
                        season_file = os.path.join(p_folder, f"{safe_name}_season.json")
                        with open(season_file, 'w', encoding='utf-8') as f:
                            json.dump(p, f, indent=4)
                            
                        p['clean_name'] = name_str
                        p['folder_name'] = safe_name
                        filtered_players.append(p)
                        count += 1
                        
                    print(f"  {count} players initialized.")
                    
                except Exception as e:
                    print(f"  Error processing players JSON: {e}")
            
            # --- PROCESS BOX SCORES ---
            print("  Fetching box scores...")
            processed_games = 0
            for game in team_data_list:
                if not isinstance(game, dict): continue
                
                box_link = game.get('boxScoreLink')
                date_fmt = game.get('eventDateFormatted', 'Unknown')
                
                if not box_link or not isinstance(box_link, str):
                    continue
                    
                # Division-specific box score URL
                box_url = f"https://njcaastats.prestosports.com/sports/mbkb/2025-26/{div_path}/boxscores/{box_link}?tmpl=bbxml-monospace-template"
                
                try:
                    stats_list = scrape_box_score(box_url, name)
                    if not stats_list:
                        continue
                        
                    for stat in stats_list:
                        scraped_name = stat['Player Name']
                        
                        matched_player = None
                        
                        for fp in filtered_players:
                            fp_name = fp['clean_name']
                            if scraped_name.lower() == fp_name.lower():
                                matched_player = fp
                                break
                            # Removed loose matching (in) to avoid misattribution
                        
                        if matched_player:
                            safe_date = sanitize_filename(date_fmt)
                            p_folder_name = matched_player['folder_name']
                            
                            filename = f"{safe_date}_{p_folder_name}.json"
                            p_dir = os.path.join(players_root, p_folder_name)
                            
                            stat['eventDateFormatted'] = date_fmt
                            
                            with open(os.path.join(p_dir, filename), 'w', encoding='utf-8') as f:
                                json.dump(stat, f, indent=4)
                                
                    processed_games += 1
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"    Error processing box score {box_link}: {e}")
            
            print(f"  {processed_games} box scores processed.")

        except Exception as e:
            print(f"  Error processing {slug}: {e}")
            
        time.sleep(1)

    print("\nStats scrape completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--division', type=str, choices=['DI', 'DII', 'DIII'],
                        help='Only scrape teams from this division')
    args = parser.parse_args()
    
    scrape_stats(args.division)
