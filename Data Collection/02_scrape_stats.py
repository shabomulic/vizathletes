import requests
import json
import os
import time
import re
from bs4 import BeautifulSoup

def sanitize_filename(name):
    # Keep alphanumerics, spaces, dashes, underscores.
    # Replace slashes with dashes.
    safe = re.sub(r'[\\/*?:"<>|]', "", name)
    return safe.strip()

def scrape_box_score(url, target_team_name):
    print(f"    Fetching box score: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            print(f"    Failed to fetch box score: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Find the table for this team.
        # Look for div.caption containing the team name.
        # Note: Team name in caption might hold ranking or record, e.g. "VISITORS: Montgomery College (MD) (0-0)"
        # We'll search for the clean name or parts of it.
        
        captions = soup.find_all("div", class_="caption")
        target_table = None
        
        # Normalize target name for matching
        norm_target = target_team_name.lower().replace(" ", "")
        
        for cap in captions:
            cap_text = cap.get_text().lower().replace(" ", "")
            # Check if target name matches
            # The caption usually starts with "VISITORS:" or "HOME:"
            if norm_target in cap_text:
                # Found the caption. The table is likely in the next sibling div.monostats-fullbox
                # or just the next table.
                # Structure: <div class="clearfix"><div class="caption">...</div><div class="monostats-fullbox"><table>...</table></div></div>
                parent = cap.parent
                fullbox = parent.find("div", class_="monostats-fullbox")
                if fullbox:
                    target_table = fullbox.find("table")
                break
        
        if not target_table:
            # Fallback: Try to match without "VISITORS/HOME" prefix if layout differs
            # For now, return empty if not found
            print(f"    Could not find table for {target_team_name}")
            return []

        # 2. Parse rows
        player_stats = []
        rows = target_table.find_all("tr")
        
        # Indices based on analysis:
        # 0:#, 1:Name, 3:FGM-A, 4:3PM-A, 5:FTM-A, 6:OREB, 7:DREB, 8:REB, 
        # 9:PF, 10:TP, 11:AST, 12:TO, 13:BLK, 14:STL, 15:MIN
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 16:
                continue
            
            # Extract Name (Index 1)
            raw_name = cells[1].get_text().strip()
            # Remove trailing dots "Iman Pascal.........."
            name = raw_name.rstrip(".").strip()
            
            # Skip if name is "Team" "Totals" etc.
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

def scrape_stats():
    # Load teams
    try:
        with open('teams.json', 'r') as f:
            teams = json.load(f)
    except FileNotFoundError:
        print("Error: teams.json not found. Run 01_scrape_rankings.py first.")
        return

    # Create data directory
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"Starting stats scrape for {len(teams)} teams...")

    for i, team in enumerate(teams):
        slug = team['slug']
        name = team['name']
        
        # URL format
        url = f"https://njcaastats.prestosports.com/sports/mbkb/2025-26/div2/teams/{slug}?tmpl=teaminfo-network-monospace-json-template"
        
        print(f"[{i+1}/{len(teams)}] Fetching stats for {name} ({slug})...")
        
        team_dir = os.path.join(output_dir, slug)
        os.makedirs(team_dir, exist_ok=True)
        
        try:
            # 1. Fetch HTML template
            response = requests.get(url, headers=headers)
            if response.status_code == 404:
                print(f"  WARNING: 404 Not Found for {slug}")
                continue
            response.raise_for_status()
            
            # 2. Extract JSON URLs
            team_match = re.search(r'(https://[^"]+/teamData/[^"]+\.json)', response.text)
            players_match = re.search(r'(https://[^"]+/playersData/[^"]+\.json)', response.text)
            
            # --- PROCESS TEAM DATA (GAMES) ---
            team_data_list = []
            my_team_id = None
            
            if team_match:
                team_json_url = team_match.group(1)
                try:
                    res = requests.get(team_json_url, headers=headers)
                    res.raise_for_status()
                    
                    # Store raw
                    with open(os.path.join(team_dir, "team.json"), 'w', encoding='utf-8') as f:
                        f.write(res.text)
                    
                    data = res.json()
                    if isinstance(data, dict):
                        if 'events' in data and isinstance(data['events'], list):
                             team_data_list = data['events']
                        else:
                             team_data_list = [v for v in data.values() if isinstance(v, dict)]
                    else:
                        team_data_list = data
                        
                    # Find Team ID
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
                        print(f"  Identified Team ID: {my_team_id}")
                    else:
                        print(f"  WARNING: Could not identify Team ID.")

                    # Save Game JSONs
                    games_dir = os.path.join(team_dir, "team")
                    os.makedirs(games_dir, exist_ok=True)
                    
                    # We iterate games again later for box scores, but let's save basic files first?
                    # User requested specific naming for team/ folder files: "eventDateFormatted".
                    # We can combine this loop with box score processing or do it here.
                    # Let's do it here.
                    
                    for game in team_data_list:
                        if not isinstance(game, dict): continue
                        
                        # Determine filename
                        date_fmt = game.get('eventDateFormatted', 'Unknown Date')
                        if date_fmt == "Unknown Date" and 'event' in game and 'date' in game['event']:
                             # Fallback if needed, but usually present
                             pass
                             
                        # Sanitize date
                        safe_date = sanitize_filename(date_fmt)
                        unique_suffix = ""
                        
                        # Handle collision
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
                        
                    # Filter and Create Folders
                    players_root = os.path.join(team_dir, "players")
                    os.makedirs(players_root, exist_ok=True)
                    
                    count = 0
                    for p in p_list:
                        if not isinstance(p, dict): continue
                        if my_team_id and p.get('teamId') != my_team_id:
                            continue
                            
                        # Extract Name
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
                        
                        # Create Player Folder
                        p_folder = os.path.join(players_root, safe_name)
                        
                        # Handle collision: If a file exists with this name (from prev structure), delete it
                        if os.path.isfile(p_folder):
                            os.remove(p_folder)
                            
                        os.makedirs(p_folder, exist_ok=True)
                        
                        # Save Season Stats
                        season_file = os.path.join(p_folder, f"{safe_name}_season.json")
                        with open(season_file, 'w', encoding='utf-8') as f:
                            json.dump(p, f, indent=4)
                            
                        # Add to list for box score matching
                        # We store: matched_name (cleaned), safe_folder_name, original_object
                        # Box scores have names like "Ian Pascal", or "Pascal, Ian".
                        # JSON usually has "Ian Pascal".
                        p['clean_name'] = name_str  # Store for matching
                        p['folder_name'] = safe_name
                        filtered_players.append(p)
                        count += 1
                        
                    print(f"  Initialized folders for {count} players.")
                    
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
                    
                # Construct URL
                # https://njcaastats.prestosports.com/sports/mbkb/2025-26/div2/boxscores/<link>?tmpl=bbxml-monospace-template
                box_url = f"https://njcaastats.prestosports.com/sports/mbkb/2025-26/div2/boxscores/{box_link}?tmpl=bbxml-monospace-template"
                
                # Scrape
                try:
                    stats_list = scrape_box_score(box_url, name)
                    if not stats_list:
                        continue
                        
                    # Match to players
                    for stat in stats_list:
                        scraped_name = stat['Player Name']
                        
                        # Find matching player in filtered_players
                        matched_player = None
                        
                        # Strategy: Exact match, then fuzzy (contains)
                        # Box score names often have first initial last name, or full name.
                        # Ex: "Tarik Bicic"
                        
                        for fp in filtered_players:
                            # Direct check
                            fp_name = fp['clean_name']
                            if scraped_name.lower() == fp_name.lower():
                                matched_player = fp
                                break
                            # Check part
                            if scraped_name.lower() in fp_name.lower() or fp_name.lower() in scraped_name.lower():
                                matched_player = fp
                                break
                        
                        if matched_player:
                            # Create Game JSON
                            # "Nov 1_TarikBicic.json"
                            safe_date = sanitize_filename(date_fmt)
                            p_folder_name = matched_player['folder_name']
                            
                            filename = f"{safe_date}_{p_folder_name}.json"
                            p_dir = os.path.join(players_root, p_folder_name)
                            
                            # Add date to stats object
                            stat['eventDateFormatted'] = date_fmt
                            
                            with open(os.path.join(p_dir, filename), 'w', encoding='utf-8') as f:
                                json.dump(stat, f, indent=4)
                                
                    processed_games += 1
                    time.sleep(0.5) # Slight delay
                    
                except Exception as e:
                    print(f"    Error processing box score {box_link}: {e}")
            
            print(f"  Processed {processed_games} box scores.")

        except Exception as e:
            print(f"  Error processing {slug}: {e}")
            
        # Be polite
        time.sleep(1)

    print("\nStats scrape completed.")

if __name__ == "__main__":
    scrape_stats()
