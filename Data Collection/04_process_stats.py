
import os
import json
import csv
import argparse

# --- Benchmark Thresholds ---
# Format: metric -> {PosGroup -> [(threshold, tier_name, score), ...]}
# Thresholds are checked in order: >= for normal, <= for inverted

BENCHMARKS = {
    'TS': {
        'Guard': [(0.60, 'Elite', 5), (0.57, 'Very Good', 4), (0.52, 'Average', 3), (0.48, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.60, 'Elite', 5), (0.57, 'Very Good', 4), (0.53, 'Average', 3), (0.49, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.63, 'Elite', 5), (0.60, 'Very Good', 4), (0.56, 'Average', 3), (0.52, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'UsageProxy': {
        'Guard': [(0.25, 'Elite', 5), (0.21, 'Very Good', 4), (0.17, 'Average', 3), (0.14, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.23, 'Elite', 5), (0.19, 'Very Good', 4), (0.15, 'Average', 3), (0.12, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.24, 'Elite', 5), (0.20, 'Very Good', 4), (0.16, 'Average', 3), (0.13, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'ScORtg': {
        'Guard': [(112, 'Elite', 5), (107, 'Very Good', 4), (100, 'Average', 3), (92, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(114, 'Elite', 5), (108, 'Very Good', 4), (102, 'Average', 3), (95, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(118, 'Elite', 5), (112, 'Very Good', 4), (105, 'Average', 3), (98, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'AST_TO': {
        'Guard': [(2.6, 'Elite', 5), (2.0, 'Very Good', 4), (1.4, 'Average', 3), (1.0, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(2.0, 'Elite', 5), (1.5, 'Very Good', 4), (1.1, 'Average', 3), (0.8, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(1.6, 'Elite', 5), (1.2, 'Very Good', 4), (0.9, 'Average', 3), (0.6, 'Below Average', 2), (None, 'Poor', 1)],
    },
    '3Ppct': {
        'Guard': [(0.38, 'Elite', 5), (0.35, 'Very Good', 4), (0.31, 'Average', 3), (0.28, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.37, 'Elite', 5), (0.34, 'Very Good', 4), (0.31, 'Average', 3), (0.28, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.35, 'Elite', 5), (0.32, 'Very Good', 4), (0.29, 'Average', 3), (0.26, 'Below Average', 2), (None, 'Poor', 1)],
    },
    '3PAr': {
        'Guard': [(0.40, 'Elite', 5), (0.30, 'Very Good', 4), (0.20, 'Average', 3), (0.12, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.35, 'Elite', 5), (0.25, 'Very Good', 4), (0.15, 'Average', 3), (0.08, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.20, 'Elite', 5), (0.12, 'Very Good', 4), (0.05, 'Average', 3), (0.02, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'FTr': {
        'Guard': [(0.35, 'Elite', 5), (0.25, 'Very Good', 4), (0.15, 'Average', 3), (0.08, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.30, 'Elite', 5), (0.22, 'Very Good', 4), (0.15, 'Average', 3), (0.09, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.45, 'Elite', 5), (0.35, 'Very Good', 4), (0.25, 'Average', 3), (0.15, 'Below Average', 2), (None, 'Poor', 1)],
    },
    '3PA_pg': {
        'Guard': [(5.0, 'Elite', 5), (3.5, 'Very Good', 4), (2.2, 'Average', 3), (1.0, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(4.0, 'Elite', 5), (3.0, 'Very Good', 4), (1.8, 'Average', 3), (0.8, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(2.5, 'Elite', 5), (1.5, 'Very Good', 4), (0.6, 'Average', 3), (0.1, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'eFG': {
        'Guard': [(0.55, 'Elite', 5), (0.52, 'Very Good', 4), (0.48, 'Average', 3), (0.44, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.56, 'Elite', 5), (0.53, 'Very Good', 4), (0.49, 'Average', 3), (0.45, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.58, 'Elite', 5), (0.55, 'Very Good', 4), (0.51, 'Average', 3), (0.47, 'Below Average', 2), (None, 'Poor', 1)],
    },
}

# Inverted benchmarks (lower is better)
BENCHMARKS_INVERTED = {
    'TO_100': {
        'Guard': [(3.0, 'Elite', 5), (3.8, 'Very Good', 4), (4.8, 'Average', 3), (6.0, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(2.6, 'Elite', 5), (3.4, 'Very Good', 4), (4.4, 'Average', 3), (5.6, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(2.0, 'Elite', 5), (2.6, 'Very Good', 4), (3.4, 'Average', 3), (4.4, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'PF_100': {
        'Guard': [(2.6, 'Elite', 5), (3.2, 'Very Good', 4), (4.0, 'Average', 3), (4.8, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(3.0, 'Elite', 5), (3.7, 'Very Good', 4), (4.5, 'Average', 3), (5.3, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(3.6, 'Elite', 5), (4.3, 'Very Good', 4), (5.1, 'Average', 3), (6.0, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'TOV': {
        'Guard': [(0.12, 'Elite', 5), (0.15, 'Very Good', 4), (0.18, 'Average', 3), (0.21, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(0.11, 'Elite', 5), (0.14, 'Very Good', 4), (0.17, 'Average', 3), (0.20, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(0.12, 'Elite', 5), (0.16, 'Very Good', 4), (0.19, 'Average', 3), (0.23, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'Stocks_100': {
        'Guard': [(3.4, 'Elite', 5), (2.8, 'Very Good', 4), (2.2, 'Average', 3), (1.6, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(3.2, 'Elite', 5), (2.6, 'Very Good', 4), (2.0, 'Average', 3), (1.4, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(4.4, 'Elite', 5), (3.6, 'Very Good', 4), (2.8, 'Average', 3), (2.0, 'Below Average', 2), (None, 'Poor', 1)],
    },
    'Reb_100': {
        'Guard': [(10.0, 'Elite', 5), (8.5, 'Very Good', 4), (7.0, 'Average', 3), (5.8, 'Below Average', 2), (None, 'Poor', 1)],
        'Wing': [(12.5, 'Elite', 5), (10.5, 'Very Good', 4), (8.5, 'Average', 3), (6.8, 'Below Average', 2), (None, 'Poor', 1)],
        'Big': [(18.0, 'Elite', 5), (15.0, 'Very Good', 4), (12.0, 'Average', 3), (9.8, 'Below Average', 2), (None, 'Poor', 1)],
    },
}

# Height benchmarks by position (in inches)
HEIGHT_BENCHMARKS = {
    'Guard': [(76, 'Elite', 5), (74, 'Very Good', 4), (72, 'Average', 3), (70, 'Below Average', 2), (None, 'Poor', 1)],
    'Wing': [(80, 'Elite', 5), (78, 'Very Good', 4), (76, 'Average', 3), (74, 'Below Average', 2), (None, 'Poor', 1)],
    'Big': [(83, 'Elite', 5), (81, 'Very Good', 4), (79, 'Average', 3), (77, 'Below Average', 2), (None, 'Poor', 1)],
}

# Position weights for composite scoring
WEIGHTS = {
    'Guard': {
        'Offense': {'TS': 0.20, 'ScORtg': 0.20, 'UsageProxy': 0.10, 'AST_TO': 0.20, 'TOV': 0.15, '3Ppct': 0.10, '3PA_pg': 0.05},
        'Defense': {'Stocks_100': 0.55, 'Reb_100': 0.15, 'PF_100': 0.30},
        'Overall': {'Off': 0.55, 'Def': 0.35, 'Height': 0.10}
    },
    'Wing': {
        'Offense': {'TS': 0.20, 'ScORtg': 0.20, 'UsageProxy': 0.10, 'AST_TO': 0.10, 'TOV': 0.15, '3Ppct': 0.10, '3PA_pg': 0.05, 'FTr': 0.10},
        'Defense': {'Stocks_100': 0.45, 'Reb_100': 0.30, 'PF_100': 0.25},
        'Overall': {'Off': 0.50, 'Def': 0.35, 'Height': 0.15}
    },
    'Big': {
        'Offense': {'TS': 0.25, 'ScORtg': 0.25, 'UsageProxy': 0.10, 'TOV': 0.15, 'FTr': 0.15, 'eFG': 0.10},
        'Defense': {'Stocks_100': 0.40, 'Reb_100': 0.45, 'PF_100': 0.15},
        'Overall': {'Off': 0.45, 'Def': 0.40, 'Height': 0.15}
    }
}

# --- Helper Functions ---

def get_benchmark_score(value, thresholds, inverted=False):
    """Returns (tier_name, score) for a value against thresholds."""
    if value is None:
        return ('N/A', 3)
    
    if inverted:
        # For inverted metrics (lower is better), check <= threshold
        for threshold, tier, score in thresholds:
            if threshold is None:
                return (tier, score)
            if value <= threshold:
                return (tier, score)
    else:
        # For normal metrics (higher is better), check >= threshold
        for threshold, tier, score in thresholds:
            if threshold is None:
                return (tier, score)
            if value >= threshold:
                return (tier, score)
    
    return ('Poor', 1)

def parse_height(h_str):
    """Parses height string to inches."""
    if not h_str: return None
    h_str = str(h_str).strip()
    h_str = h_str.replace('"', '').replace("'", "-").replace(" ", "-")
    
    if "-" in h_str:
        parts = h_str.split("-")
        try:
            ft = int(parts[0])
            inch = int(parts[1]) if len(parts) > 1 and parts[1] else 0
            return ft * 12 + inch
        except ValueError:
            pass
    
    try:
        val = int(h_str)
        if 50 < val < 90:
            return val
    except ValueError:
        pass
        
    return None

def format_height(height_in):
    """Converts height in inches to ft'in format."""
    if height_in is None:
        return None
    ft = int(height_in // 12)
    inch = int(height_in % 12)
    return f"{ft}'{inch}"

def normalize_position(pos_str, height_in):
    """Normalizes position to Guard, Wing, Big."""
    if not pos_str:
        return infer_position_from_height(height_in)
    
    p = pos_str.upper()
    
    if "C" in p: return "Big"
    if "G" in p and "F" in p: return "Wing"
    if "G" in p: return "Guard"
    if "F" in p:
        if height_in and height_in >= 80: return "Big"
        return "Wing"
        
    return infer_position_from_height(height_in)

def infer_position_from_height(h):
    if not h: return "Wing"
    if h <= 74: return "Guard"
    if h <= 79: return "Wing"
    return "Big"

def safe_div(n, d, default=None):
    if d == 0 or d is None: return default
    return n / d

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

# --- Main Logic ---

def process_stats(target_slug=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    # 1. Load Team Stats
    team_stats_map = {}
    schools = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    print("Loading team stats...")
    for slug in schools:
        team_dir = os.path.join(data_dir, slug, 'team')
        if not os.path.exists(team_dir): continue
        
        for fname in os.listdir(team_dir):
            if not fname.endswith('.json'): continue
            path = os.path.join(team_dir, fname)
            data = load_json(path)
            if not data or 'stats' not in data: continue
            
            date = data.get('eventDateFormatted')
            if not date: continue
            
            s = data['stats']
            
            def get_f(k):
                v = s.get(k)
                if v:
                    try: return float(v.split('-')[0])
                    except: return 0.0
                return 0.0
                
            t_poss = get_f('tposs')
            t_fga = get_f('fga')
            t_fta = get_f('fta')
            t_oreb = get_f('oreb')
            t_to = get_f('to')
            
            if t_poss == 0:
                t_poss = t_fga + 0.44 * t_fta - t_oreb + t_to
            
            team_denom = t_fga + 0.44 * t_fta + t_to
            
            team_stats_map[(slug, date)] = {
                'TeamPoss': t_poss,
                'TeamDenom': team_denom
            }

    print(f"Loaded {len(team_stats_map)} team games.")

    # 2. Aggregate Players
    all_players = []
    
    print("Aggregating player stats...")
    
    for slug in schools:
        players_dir = os.path.join(data_dir, slug, 'players')
        roster_path = os.path.join(data_dir, slug, 'roster.json')
        
        roster = load_json(roster_path)
        roster_map = {}
        if roster:
            for p in roster:
                nm = p.get('name', '').strip()
                if nm: roster_map[nm.lower()] = p
        
        if not os.path.exists(players_dir): continue
        
        for p_folder in os.listdir(players_dir):
            p_path = os.path.join(players_dir, p_folder)
            if not os.path.isdir(p_path): continue
            
            agg = {
                'PTS': 0, 'FGM': 0, 'FGA': 0, '3PM': 0, '3PA': 0, 'FTM': 0, 'FTA': 0,
                'OREB': 0, 'DREB': 0, 'REB': 0, 'AST': 0, 'TO': 0, 'STL': 0, 'BLK': 0, 'PF': 0,
                'GamesPlayed': 0,
                'TeamPossSum': 0,
                'TeamDenomSum': 0
            }
            
            player_name_clean = p_folder.replace("_", " ")
            season_path = os.path.join(p_path, f"{p_folder}_season.json")
            season_data = load_json(season_path)
            
            real_name = player_name_clean
            if season_data:
                real_name = season_data.get('fullName') or f"{season_data.get('firstName')} {season_data.get('lastName')}"
            
            r_info = roster_map.get(real_name.lower())
            
            for g_file in os.listdir(p_path):
                if g_file.endswith('_season.json'): continue
                if not g_file.endswith('.json'): continue
                
                g_data = load_json(os.path.join(p_path, g_file))
                if not g_data: continue
                
                def p_stat(k):
                    v = g_data.get(k, '0')
                    if '-' in v: return v
                    try: return float(v)
                    except: return 0.0

                date = g_data.get('eventDateFormatted')
                agg['GamesPlayed'] += 1
                
                fg = p_stat("FGM-A")
                if isinstance(fg, str) and '-' in fg:
                    m, a = fg.split('-')
                    agg['FGM'] += float(m)
                    agg['FGA'] += float(a)
                
                fg3 = p_stat("3PM-A")
                if isinstance(fg3, str) and '-' in fg3:
                    m, a = fg3.split('-')
                    agg['3PM'] += float(m)
                    agg['3PA'] += float(a)
                    
                ft = p_stat("FTM-A")
                if isinstance(ft, str) and '-' in ft:
                    m, a = ft.split('-')
                    agg['FTM'] += float(m)
                    agg['FTA'] += float(a)
                
                agg['PTS'] += float(p_stat("TP") or 0)
                agg['OREB'] += float(p_stat("OREB") or 0)
                agg['DREB'] += float(p_stat("DREB") or 0)
                agg['REB']  += float(p_stat("REB") or 0)
                agg['AST']  += float(p_stat("AST") or 0)
                agg['TO']   += float(p_stat("TO") or 0)
                agg['STL']  += float(p_stat("STL") or 0)
                agg['BLK']  += float(p_stat("BLK") or 0)
                agg['PF']   += float(p_stat("PF") or 0)
                
                ts = team_stats_map.get((slug, date))
                if ts:
                    agg['TeamPossSum'] += ts['TeamPoss']
                    agg['TeamDenomSum'] += ts['TeamDenom']

            if agg['GamesPlayed'] < 6:
                continue
                
            p_obj = {
                'TeamSlug': slug,
                'PlayerName': real_name,
                'Number': r_info.get('number') if r_info else None,
                'ClassYear': r_info.get('class_year') if r_info else None,
                'RosterPosRaw': r_info.get('position') if r_info else None,
                'HeightRaw': r_info.get('height') if r_info else None,
                'Weight': r_info.get('weight') if r_info else None,
                'GamesPlayed': agg['GamesPlayed'],
            }
            
            # Height parsing
            p_obj['HeightIn'] = parse_height(p_obj['HeightRaw'])
            p_obj['Height'] = format_height(p_obj['HeightIn'])
            p_obj['PosGroup'] = normalize_position(p_obj['RosterPosRaw'], p_obj['HeightIn'])
            
            # --- Metrics ---
            poss_used = agg['FGA'] + 0.44 * agg['FTA'] + agg['TO']
            
            p_obj['TS'] = safe_div(agg['PTS'], 2 * (agg['FGA'] + 0.44 * agg['FTA']))
            p_obj['eFG'] = safe_div(agg['FGM'] + 0.5 * agg['3PM'], agg['FGA'])
            p_obj['ScORtg'] = safe_div(100 * agg['PTS'], poss_used)
            p_obj['UsageProxy'] = safe_div(poss_used, agg['TeamDenomSum'])
            
            if agg['TO'] > 0:
                p_obj['AST_TO'] = agg['AST'] / agg['TO']
            elif agg['AST'] > 0:
                p_obj['AST_TO'] = 99.0
            else:
                p_obj['AST_TO'] = None
                
            p_obj['TOV'] = safe_div(agg['TO'], poss_used)
            p_obj['3Ppct'] = safe_div(agg['3PM'], agg['3PA'])
            p_obj['3PAr'] = safe_div(agg['3PA'], agg['FGA'])
            p_obj['FTr'] = safe_div(agg['FTA'], agg['FGA'])
            
            t_poss_sum = agg['TeamPossSum']
            p_obj['TO_100'] = safe_div(100 * agg['TO'], t_poss_sum)
            p_obj['Stocks_100'] = safe_div(100 * (agg['STL'] + agg['BLK']), t_poss_sum)
            p_obj['Reb_100'] = safe_div(100 * agg['REB'], t_poss_sum)
            p_obj['PF_100'] = safe_div(100 * agg['PF'], t_poss_sum)
            
            # Per-game metrics
            gp = agg['GamesPlayed']
            p_obj['PTS_pg'] = agg['PTS'] / gp
            p_obj['REB_pg'] = agg['REB'] / gp
            p_obj['AST_pg'] = agg['AST'] / gp
            p_obj['TO_pg'] = agg['TO'] / gp
            p_obj['STL_pg'] = agg['STL'] / gp
            p_obj['BLK_pg'] = agg['BLK'] / gp
            p_obj['PF_pg'] = agg['PF'] / gp
            p_obj['FGA_pg'] = agg['FGA'] / gp
            p_obj['3PA_pg'] = agg['3PA'] / gp
            p_obj['FTA_pg'] = agg['FTA'] / gp
            p_obj['OREB_pg'] = agg['OREB'] / gp
            p_obj['DREB_pg'] = agg['DREB'] / gp
            
            # Store total 3PA for volume check
            p_obj['3PA_total'] = agg['3PA']

            all_players.append(p_obj)

    print(f"Total players included: {len(all_players)}")
    
    # 3. Apply Benchmark Scoring
    for p in all_players:
        pg = p['PosGroup']
        
        # Normal metrics
        for metric in ['TS', 'UsageProxy', 'ScORtg', 'AST_TO', '3PAr', 'FTr', '3PA_pg', 'eFG']:
            if metric in BENCHMARKS and pg in BENCHMARKS[metric]:
                val = p.get(metric)
                tier, score = get_benchmark_score(val, BENCHMARKS[metric][pg], inverted=False)
                p[f'{metric}_Tier'] = tier
                p[f'{metric}_Score'] = score
        
        # 3P% with volume guardrail
        if p.get('3PA_total', 0) < 25:
            p['3Ppct_Tier'] = 'Insufficient Volume'
            p['3Ppct_Score'] = 3
        else:
            val = p.get('3Ppct')
            tier, score = get_benchmark_score(val, BENCHMARKS['3Ppct'][pg], inverted=False)
            p['3Ppct_Tier'] = tier
            p['3Ppct_Score'] = score
        
        # Inverted metrics (need special handling for Stocks and Reb which are normal)
        for metric in ['TO_100', 'PF_100', 'TOV']:
            if metric in BENCHMARKS_INVERTED and pg in BENCHMARKS_INVERTED[metric]:
                val = p.get(metric)
                tier, score = get_benchmark_score(val, BENCHMARKS_INVERTED[metric][pg], inverted=True)
                p[f'{metric}_Tier'] = tier
                p[f'{metric}_Score'] = score
        
        # Stocks and Reb are normal (higher is better)
        for metric in ['Stocks_100', 'Reb_100']:
            if metric in BENCHMARKS_INVERTED and pg in BENCHMARKS_INVERTED[metric]:
                val = p.get(metric)
                tier, score = get_benchmark_score(val, BENCHMARKS_INVERTED[metric][pg], inverted=False)
                p[f'{metric}_Tier'] = tier
                p[f'{metric}_Score'] = score
        
        # Height scoring
        if p['HeightIn'] is None:
            p['Height_Tier'] = 'Unknown'
            p['HeightScore'] = 3
        else:
            tier, score = get_benchmark_score(p['HeightIn'], HEIGHT_BENCHMARKS[pg], inverted=False)
            p['Height_Tier'] = tier
            p['HeightScore'] = score
    
    # 4. Compute Composite Scores
    for p in all_players:
        pg = p['PosGroup']
        w = WEIGHTS.get(pg, WEIGHTS['Wing'])
        
        # Offense
        off_score_sum = 0
        off_weight_sum = 0
        for metric, weight in w['Offense'].items():
            score = p.get(f'{metric}_Score', 3)
            off_score_sum += score * weight
            off_weight_sum += weight
        p['OffScore'] = off_score_sum / off_weight_sum if off_weight_sum > 0 else 3.0
        
        # Defense
        def_score_sum = 0
        def_weight_sum = 0
        for metric, weight in w['Defense'].items():
            score = p.get(f'{metric}_Score', 3)
            def_score_sum += score * weight
            def_weight_sum += weight
        p['DefScore'] = def_score_sum / def_weight_sum if def_weight_sum > 0 else 3.0
        
        # Overall
        p['Overall'] = (
            p['OffScore'] * w['Overall']['Off'] +
            p['DefScore'] * w['Overall']['Def'] +
            p['HeightScore'] * w['Overall']['Height']
        )
        
    # 5. Output CSVs
    all_players.sort(key=lambda x: (x['Overall'], x['OffScore'], x['DefScore'], x['GamesPlayed']), reverse=True)
    
    for i, p in enumerate(all_players):
        p['MasterRank'] = i + 1
        
    cols = [
        'MasterRank', 'TeamRank', 'TeamSlug', 'PlayerName', 'Number', 'ClassYear', 'RosterPosRaw', 'PosGroup',
        'Height', 'Weight', 'GamesPlayed', 'Overall', 'OffScore', 'DefScore', 'HeightScore',
        'PTS_pg', 'REB_pg', 'AST_pg', 'TO_pg', 'STL_pg', 'BLK_pg', 'PF_pg', 
        'FGA_pg', '3PA_pg', 'FTA_pg', 'OREB_pg', 'DREB_pg',
        'TS', 'eFG', 'ScORtg', 'UsageProxy', 'AST_TO', 'TOV', '3Ppct', '3PAr', 'FTr',
        'TO_100', 'Stocks_100', 'Reb_100', 'PF_100',
        'TS_Tier', 'TS_Score', 'UsageProxy_Tier', 'UsageProxy_Score', 
        'ScORtg_Tier', 'ScORtg_Score', 'AST_TO_Tier', 'AST_TO_Score',
        'TOV_Tier', 'TOV_Score', '3Ppct_Tier', '3Ppct_Score', 
        '3PA_pg_Tier', '3PA_pg_Score', '3PAr_Tier', '3PAr_Score',
        'FTr_Tier', 'FTr_Score', 'eFG_Tier', 'eFG_Score',
        'Stocks_100_Tier', 'Stocks_100_Score', 'Reb_100_Tier', 'Reb_100_Score',
        'PF_100_Tier', 'PF_100_Score', 'TO_100_Tier', 'TO_100_Score',
        'Height_Tier'
    ]
    
    # Write Master
    master_path = os.path.join(data_dir, 'master_all_players_ranked.csv')
    with open(master_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_players)
        
    print(f"Saved master CSV to {master_path}")
    
    # Write Team CSVs
    teams_data = {}
    for p in all_players:
        s = p['TeamSlug']
        if s not in teams_data: teams_data[s] = []
        teams_data[s].append(p)
        
    for slug, players in teams_data.items():
        for i, p in enumerate(players):
            p['TeamRank'] = i + 1
            
        csv_path = os.path.join(data_dir, slug, f"{slug}_ranked.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(players)
        
        if target_slug and slug == target_slug:
             print(f"Saved target CSV to {csv_path}")

    # Sanity outputs
    print(f"\n--- Sanity Check ---")
    print(f"Teams processed: {len(teams_data)}")
    print(f"Players included: {len(all_players)}")
    
    print("\nTop 25 Players (Master):")
    for p in all_players[:25]:
        print(f"{p['MasterRank']:3}. {p['PlayerName']:<25} ({p['TeamSlug']:<30}) Overall: {p['Overall']:.2f}  Off: {p['OffScore']:.2f}  Def: {p['DefScore']:.2f}")

    if target_slug:
        print(f"\nTop 10 Players ({target_slug}):")
        target_players = teams_data.get(target_slug, [])
        for p in target_players[:10]:
            print(f"{p['TeamRank']:3}. {p['PlayerName']:<25} Overall: {p['Overall']:.2f}  Off: {p['OffScore']:.2f}  Def: {p['DefScore']:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=str, help='Target team slug to focus validation on')
    args = parser.parse_args()
    
    process_stats(args.target)
