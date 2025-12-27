"""
01_scrape_teams.py

Scrapes ALL teams from NJCAA stats for DI, DII, and DIII divisions.
Uses browser automation to navigate paginated tables.

Source: https://njcaastats.prestosports.com/sports/mbkb/teams-page
- Division I: 186 teams (10 pages)
- Division II: 157 teams (8 pages)
- Division III: 90 teams (5 pages)
"""

import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Division config
DIVISIONS = {
    'DI': {
        'tab_id': 'team-listing-tab1',
        'pages': 10,
        'name': 'Division I'
    },
    'DII': {
        'tab_id': 'team-listing-tab2', 
        'pages': 8,
        'name': 'Division II'
    },
    'DIII': {
        'tab_id': 'team-listing-tab3',
        'pages': 5,
        'name': 'Division III'
    }
}

URL = "https://njcaastats.prestosports.com/sports/mbkb/teams-page"


def create_driver():
    """Create headless Chrome driver."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    return webdriver.Chrome(options=options)


def scrape_division(driver, div_code, config):
    """Scrape all teams from a division tab."""
    teams = []
    
    print(f"\nScraping {config['name']} ({config['pages']} pages)...")
    
    # Click the division tab
    tab = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, config['tab_id']))
    )
    tab.click()
    time.sleep(2)  # Wait for table to load
    
    for page_num in range(config['pages']):
        print(f"  Page {page_num + 1}/{config['pages']}...", end=" ")
        
        # Wait for table rows to be present
        time.sleep(1)
        
        # Find all team rows in the current table
        try:
            # The table is inside a tab content div
            table = driver.find_element(By.CSS_SELECTOR, f"#team-listing-tab-content{div_code[-1]} table")
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            page_teams = 0
            for row in rows:
                try:
                    # Get team name from the link
                    link = row.find_element(By.CSS_SELECTOR, "td a")
                    team_name = link.text.strip()
                    href = link.get_attribute("href")
                    
                    # Extract slug from URL
                    # Format: .../teams/{slug}
                    if "/teams/" in href:
                        slug = href.split("/teams/")[-1].split("?")[0].strip("/")
                    else:
                        slug = team_name.lower().replace(" ", "").replace("'", "")
                    
                    if team_name and slug:
                        teams.append({
                            'name': team_name,
                            'slug': slug,
                            'division': div_code
                        })
                        page_teams += 1
                except Exception:
                    continue
            
            print(f"found {page_teams} teams")
            
        except Exception as e:
            print(f"Error: {e}")
        
        # Click next page if not on last page
        if page_num < config['pages'] - 1:
            try:
                # Find the next button in the pagination
                next_btn = driver.find_element(
                    By.CSS_SELECTOR, 
                    f"#team-listing-tab-content{div_code[-1]} .dataTables_paginate .next"
                )
                if 'disabled' not in next_btn.get_attribute('class'):
                    next_btn.click()
                    time.sleep(1.5)
            except Exception as e:
                print(f"  Pagination error: {e}")
                break
    
    return teams


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    teams_path = os.path.join(base_dir, 'teams.json')
    
    # Load existing teams if any
    existing_teams = {}
    if os.path.exists(teams_path):
        with open(teams_path, 'r', encoding='utf-8') as f:
            for team in json.load(f):
                existing_teams[team['slug']] = team
    
    print(f"Starting team scrape from {URL}")
    print(f"Existing teams in teams.json: {len(existing_teams)}")
    
    driver = create_driver()
    all_teams = []
    
    try:
        driver.get(URL)
        time.sleep(3)  # Initial page load
        
        for div_code, config in DIVISIONS.items():
            teams = scrape_division(driver, div_code, config)
            all_teams.extend(teams)
            print(f"  {config['name']}: {len(teams)} teams scraped")
    
    finally:
        driver.quit()
    
    # Merge with existing teams (preserve any extra data)
    final_teams = []
    seen_slugs = set()
    
    for team in all_teams:
        slug = team['slug']
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        
        if slug in existing_teams:
            # Merge - keep existing data, update division
            merged = existing_teams[slug].copy()
            merged['division'] = team['division']
            merged['name'] = team['name']  # Use fresh name
            final_teams.append(merged)
        else:
            final_teams.append(team)
    
    # Sort by division, then name
    final_teams.sort(key=lambda x: (x['division'], x['name']))
    
    # Save
    with open(teams_path, 'w', encoding='utf-8') as f:
        json.dump(final_teams, f, indent=4)
    
    print(f"\n=== Summary ===")
    di_count = len([t for t in final_teams if t['division'] == 'DI'])
    dii_count = len([t for t in final_teams if t['division'] == 'DII'])
    diii_count = len([t for t in final_teams if t['division'] == 'DIII'])
    
    print(f"Division I:   {di_count} teams")
    print(f"Division II:  {dii_count} teams")
    print(f"Division III: {diii_count} teams")
    print(f"Total:        {len(final_teams)} teams")
    print(f"Saved to {teams_path}")


if __name__ == "__main__":
    main()
