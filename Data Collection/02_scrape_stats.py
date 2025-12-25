import requests
import json
import os
import time
import re

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
        
        # Construct URL
        # URL format: https://njcaastats.prestosports.com/sports/mbkb/2025-26/div2/teams/<slug>?tmpl=teaminfo-network-monospace-json-template
        url = f"https://njcaastats.prestosports.com/sports/mbkb/2025-26/div2/teams/{slug}?tmpl=teaminfo-network-monospace-json-template"
        
        print(f"[{i+1}/{len(teams)}] Fetching stats for {name} ({slug})...")
        
        # Create team directory
        team_dir = os.path.join(output_dir, slug)
        os.makedirs(team_dir, exist_ok=True)
        
        try:
            # 1. Fetch the HTML template page
            response = requests.get(url, headers=headers)
            if response.status_code == 404:
                print(f"  WARNING: 404 Not Found for {slug}")
                continue
            response.raise_for_status()
            
            # 2. Extract the actual JSON URLs from the script tag
            team_match = re.search(r'(https://[^"]+/teamData/[^"]+\.json)', response.text)
            players_match = re.search(r'(https://[^"]+/playersData/[^"]+\.json)', response.text)
            
            # Fetch and save Team Data
            if team_match:
                team_json_url = team_match.group(1)
                try:
                    team_json_res = requests.get(team_json_url, headers=headers)
                    team_json_res.raise_for_status()
                    
                    # Store raw JSON
                    with open(os.path.join(team_dir, "team.json"), 'w', encoding='utf-8') as f:
                        f.write(team_json_res.text)
                    
                    team_data = team_json_res.json()
                    
                    # Split into per-game files in 'team' subfolder
                    games_dir = os.path.join(team_dir, "team")
                    os.makedirs(games_dir, exist_ok=True)
                    
                    # EXTRACTION LOGIC
                    if isinstance(team_data, dict):
                        if 'events' in team_data and isinstance(team_data['events'], list):
                             team_data_list = team_data['events']
                        else:
                             # Filter to get only game objects (which should be dicts)
                             team_data_list = [v for v in team_data.values() if isinstance(v, dict)]
                        print(f"  Notice: Number of games/events found: {len(team_data_list)}")
                    else:
                        team_data_list = team_data

                    for game in team_data_list:
                        if not isinstance(game, dict):
                            continue
                        
                        game_id = None
                        if 'event' in game and isinstance(game['event'], dict) and 'eventId' in game['event']:
                            game_id = game['event']['eventId']
                        elif 'eventId' in game: 
                             game_id = game['eventId']
                        elif 'stats' in game and 'event' in game: 
                             if 'eventId' in game['event']:
                                 game_id = game['event']['eventId']
                        
                        if not game_id:
                            continue
                            
                        game_filename = f"{game_id}.json"
                        with open(os.path.join(games_dir, game_filename), 'w', encoding='utf-8') as f:
                            json.dump(game, f, indent=4)
                            
                    # Find the correct Team ID for this school
                    my_team_id = None
                    # We can find it in the stats/events
                    for game in team_data_list:
                        if not isinstance(game, dict):
                             continue
                        if 'event' in game and 'teams' in game['event']:
                            teams_in_game = game['event']['teams']
                            for t in teams_in_game:
                                # Try to match by name
                                # We have 'name' from teams.json
                                if t.get('name') == name:
                                    my_team_id = t.get('teamId')
                                    break
                                # Fallback: simplified match
                                if t.get('name').lower().replace(' ','') == name.lower().replace(' ',''):
                                    my_team_id = t.get('teamId')
                                    break
                        if my_team_id:
                            break
                    
                    if my_team_id:
                         print(f"  Identified Team ID: {my_team_id}")
                    else:
                         print(f"  WARNING: Could not identify Team ID for {name}. Player filtering might fail.")

                except Exception as e:
                    print(f"  Error fetching/processing team JSON: {e}")

            # Fetch and save Players Data
            if players_match:
                players_json_url = players_match.group(1)
                try:
                    players_json_res = requests.get(players_json_url, headers=headers)
                    players_json_res.raise_for_status()
                    
                    # Store raw JSON
                    with open(os.path.join(team_dir, "players.json"), 'w', encoding='utf-8') as f:
                        f.write(players_json_res.text)
                        
                    players_data = players_json_res.json()
                    
                    # Split into per-player files in 'players' subfolder
                    players_subdir = os.path.join(team_dir, "players")
                    os.makedirs(players_subdir, exist_ok=True)
                    
                    # EXTRACTION LOGIC
                    if isinstance(players_data, dict):
                        if 'individuals' in players_data and isinstance(players_data['individuals'], list):
                             players_data_list = players_data['individuals']
                        else:
                             players_data_list = [v for v in players_data.values() if isinstance(v, dict)]
                        print(f"  Notice: Raw player list size: {len(players_data_list)}")
                    else:
                        players_data_list = players_data
                    
                    saved_count = 0
                    for player in players_data_list:
                        if not isinstance(player, dict):
                            continue
                        
                        # FILTER BY TEAM ID
                        if my_team_id:
                            p_team_id = player.get('teamId')
                            if p_team_id != my_team_id:
                                continue
                        
                        full_name = player.get('fullName', '').strip()
                        first = player.get('firstName', '').strip()
                        last = player.get('lastName', '').strip()
                        p_id = player.get('playerId', 'unknown')
                        
                        if full_name:
                            clean_name = re.sub(r'[^a-zA-Z0-9]', '', full_name)
                            filename = f"{clean_name}.json"
                        elif first and last:
                            clean_name = re.sub(r'[^a-zA-Z0-9]', '', f"{first}_{last}")
                            filename = f"{clean_name}.json"
                        else:
                            filename = f"{p_id}.json"
                            
                        with open(os.path.join(players_subdir, filename), 'w', encoding='utf-8') as f:
                            json.dump(player, f, indent=4)
                        saved_count += 1
                            
                    print(f"  Saved {saved_count} players to {players_subdir}")

                except Exception as e:
                    print(f"  Error fetching/processing players JSON: {e}")

        except Exception as e:
            print(f"  Error processing {slug}: {e}")
            
        # Be polite
        time.sleep(1)

    print("\nStats scrape completed.")

if __name__ == "__main__":
    scrape_stats()
