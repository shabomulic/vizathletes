import requests
from bs4 import BeautifulSoup
import json
import re

def get_slug(name):
    # Remove punctuation, spaces to dashes, lowercase
    # Example: "Des Moines Area Community College" -> "desmoinesareacommunitycollege"
    # Actually, the previous slug inspection showed just lowercasing and removing spaces/punctuation
    # e.g. "desmoinesareacommunitycollege"
    # Let's match the slug pattern we observed in the URLs
    
    # Remove parens and their content? No, names in teams.json were like "Bryant and Stratton College (WI)"
    # and slug was "bryantandstrattoncollegewi"
    
    clean = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    return clean

def scrape_rankings():
    url = "https://www.njcaa.org/sports/mbkb/rankings/DII/index"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Rankings are usually in a table
        # Look for the main rankings table
        # Table structure likely: <table>...<tr><th>Rank</th><th>Team</th>...
        
        table = soup.find("table")
        if not table:
            print("Error: Could not find rankings table.")
            return

        teams = []
        rows = table.find_all("tr")
        
        # Skip header row
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
                
            # Column mapping based on teams.json schema:
            # Rank | Team | Division | Region | Record | Points | 1st Place Votes | Previous Rank
            
            # Check cell count to be safe
            if len(cells) < 8:
                continue

            rank = cells[0].get_text(strip=True)
            team_name = cells[1].get_text(strip=True)
            division = cells[2].get_text(strip=True)
            region = cells[3].get_text(strip=True)
            record = cells[4].get_text(strip=True)
            points = cells[5].get_text(strip=True)
            first_place = cells[6].get_text(strip=True)
            previous = cells[7].get_text(strip=True)
            
            # Generate slug
            slug = get_slug(team_name)
            
            team_data = {
                "rank": rank,
                "name": team_name,
                "slug": slug,
                "division": division,
                "region": region,
                "record": record,
                "points": points,
                "first_place_votes": first_place,
                "previous_rank": previous
            }
            
            teams.append(team_data)

        if teams:
            with open("teams.json", "w") as f:
                json.dump(teams, f, indent=4)
            print(f"Successfully scraped {len(teams)} teams to teams.json")
        else:
            print("No teams found in table.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    scrape_rankings()
