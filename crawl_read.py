import requests
import pandas as pd
import time
from collections import deque

# ========== SETTINGS ==========
SEED_PLAYER_LIMIT = 2           # Start with this many top players
MAX_TOTAL_PLAYERS = 3000           # Crawl this many unique players
MATCHES_PER_PLAYER = 20          # Max matches per player
CRAWL_DEPTH_THROTTLE = 0.05        # Sleep between API calls (seconds)

# ========== FUNCTIONS ==========

def get_leaderboard_players(limit, offset=0):
    url = f"https://aoe4world.com/api/v0/leaderboards/rm_solo?limit={limit}&offset={offset}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    data = response.json()
    return [p['profile_id'] for p in data.get('players', [])]


def get_all_matches_for_player(profile_id, max_matches):
    matches = []
    offset = 0
    batch_size = 100

    while len(matches) < max_matches:
        url = f"https://aoe4world.com/api/v0/players/{profile_id}/games?limit={batch_size}&offset={offset}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching matches for {profile_id}: {response.status_code}")
            break
        data = response.json()
        new_matches = data.get('games', [])
        if not new_matches:
            break
        matches.extend(new_matches)
        offset += batch_size
        time.sleep(CRAWL_DEPTH_THROTTLE)

    return matches[:max_matches]


def extract_features_from_match(match):
    if 'teams' not in match or len(match['teams']) != 2:
        return None  # Ignore FFA or broken match data

    try:
        team_A = match['teams'][0]
        team_B = match['teams'][1]
        team_size = len(team_A)

        def team_features(team):
            mmrs = [p['player'].get("mmr") for p in team if p['player'].get("mmr") is not None]
            civs = [p['player'].get("civilization", "Unknown") for p in team]
            if not mmrs:
                return 0, civs
            return sum(mmrs) / len(mmrs), civs

        mmr_A, civs_A = team_features(team_A)
        mmr_B, civs_B = team_features(team_B)

        result = int(any(p['player'].get("result", "").lower() == "win" for p in team_A))

        return {
            "team_size": team_size,
            "team_A_avg_mmr": mmr_A,
            "team_B_avg_mmr": mmr_B,
            "team_A_civs": ",".join(civs_A),
            "team_B_civs": ",".join(civs_B),
            "map_name": match.get("map", "Unknown"),
            "team_A_won": result
        }

    except Exception as e:
        print("Error extracting features:", e)
        return None


def crawl_players(seed_players, max_players, matches_per_player):
    seen_players = set(seed_players)
    queue = deque(seed_players)
    data_1v1, data_team = [], []

    while queue and len(seen_players) < max_players:
        pid = queue.popleft()
        print(f"Processing player {pid} ({len(seen_players)}/{max_players})...")
        matches = get_all_matches_for_player(pid, matches_per_player)
        for match in matches:
            features = extract_features_from_match(match)
            if features:
                if features["team_size"] == 1:
                    data_1v1.append(features)
                else:
                    data_team.append(features)

            # Expand player pool with opponents
            if 'teams' in match:
                
                current_mmr = None
                
                for team in match['teams']:
                    for p in team:
                        if p['player'].get('profile_id') == pid:
                            current_mmr = p['player'].get('mmr', None)
                            break
                    if current_mmr is not None:
                        break
                    
                for team in match['teams']:
                    for p in team:
                        opid = p['player'].get('profile_id')
                        opp_mmr = p['player'].get('mmr', None)

                        # Only add if not already seen AND has lower MMR than current player
                        if (
                            opid 
                            and opid != pid 
                            and opid not in seen_players 
                            and current_mmr is not None 
                            and opp_mmr is not None 
                            and (opp_mmr + 100) < current_mmr
                            ):
                            print(f"Current mmr: {current_mmr}")
                            print(f"Opponent mmr: {opp_mmr}")
                            seen_players.add(opid)
                            queue.append(opid)
                            if len(seen_players) >= max_players:
                                break
                    if len(seen_players) >= max_players:
                        break
        time.sleep(CRAWL_DEPTH_THROTTLE)

    return pd.DataFrame(data_1v1), pd.DataFrame(data_team)


# ========== MAIN EXECUTION ==========

if __name__ == "__main__":
    print("Getting seed players from leaderboard...")
    seed_players = get_leaderboard_players(SEED_PLAYER_LIMIT)

    print("Starting crawl...")
    df_1v1, df_team = crawl_players(seed_players, MAX_TOTAL_PLAYERS, MATCHES_PER_PLAYER)


    # Save
    df_1v1.to_csv("aoe4_1v1_matches.csv", index=False)
    df_team.to_csv("aoe4_team_matches.csv", index=False)

    print(f"Saved {len(df_1v1)} 1v1 matches and {len(df_team)} team matches.")
