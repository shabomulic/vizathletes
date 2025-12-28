import os
import json
import shutil

def cleanup():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    
    divisions = ['Division I', 'Division II', 'Division III']
    
    for div in divisions:
        div_path = os.path.join(data_dir, div)
        if not os.path.exists(div_path):
            continue
            
        print(f"Checking {div}...")
        teams = [d for d in os.listdir(div_path) if os.path.isdir(os.path.join(div_path, d))]
        
        for slug in teams:
            team_dir = os.path.join(div_path, slug)
            players_dir = os.path.join(team_dir, 'players')
            roster_path = os.path.join(team_dir, 'roster.json')
            
            if not os.path.exists(players_dir):
                continue
                
            # Load roster names
            roster_names = set()
            if os.path.exists(roster_path):
                try:
                    with open(roster_path, 'r', encoding='utf-8') as f:
                        roster_data = json.load(f)
                        for p in roster_data:
                            name = p.get('name', '').strip()
                            if name:
                                # We need to match the folder names which are sanitized
                                # In 02_scrape_stats.py, safe_name = sanitize_filename(name_str)
                                roster_names.add(name.lower().replace(' ', '').replace('.', '').replace("'", "").replace('-', ''))
                except Exception as e:
                    print(f"  Error loading roster for {slug}: {e}")
            else:
                # If no roster, we might not want to delete everything blindly
                # But if there are > 50 players, it's almost certainly corrupted
                player_folders = [d for d in os.listdir(players_dir) if os.path.isdir(os.path.join(players_dir, d))]
                if len(player_folders) > 50:
                    print(f"  [WARNING] {slug} has {len(player_folders)} players but no roster.json. Skipping for safety.")
                continue

            # Now check player folders
            player_folders = [d for d in os.listdir(players_dir) if os.path.isdir(os.path.join(players_dir, d))]
            
            deleted_count = 0
            for folder in player_folders:
                # Normalize folder name for comparison
                norm_folder = folder.lower().replace(' ', '').replace('.', '').replace("'", "").replace('-', '')
                
                if norm_folder not in roster_names:
                    # Special case: check if it contains 'Player_' (fallback ID)
                    if folder.startswith('Player_'):
                        continue
                        
                    shutil.rmtree(os.path.join(players_dir, folder))
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"  {slug}: Deleted {deleted_count} misattributed player folders. {len(player_folders) - deleted_count} remain.")

if __name__ == "__main__":
    cleanup()
