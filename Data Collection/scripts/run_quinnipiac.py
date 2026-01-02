from scrape_maac import scrape_roster, scrape_schedule, process_season_stats, sanitize_team_folder, DATA_DIR, extract_name_parts
import os
import time

team = "Quinnipiac University"
roster_url = "https://gobobcats.com/sports/mens-basketball/roster?view=2"
schedule_url = "https://gobobcats.com/sports/mens-basketball/schedule/2025-26?grid=true"

print(f"Running fix for {team}...")

team_folder = sanitize_team_folder(team)
team_dir = os.path.join(DATA_DIR, team_folder)

roster = scrape_roster(team, roster_url)
print(f"Roster size: {len(roster)}")

if roster:
    p_map = {}
    for p in roster:
        parts = tuple(sorted(extract_name_parts(p['name'])))
        p_map[parts] = p['name']
        
    scrape_schedule(team, schedule_url, team_dir, p_map)
    process_season_stats(team, team_dir)
print("Done.")
