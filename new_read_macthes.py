import requests
import pandas as pd
import time
import random

def get_leaderboard_players(limit, max_offset=5000000):
    players = set()
    batch_size = 100
    all_offsets = list(range(0, max_offset, batch_size))
    random.shuffle(all_offsets)

    for offset in all_offsets:
        if len(players) >= limit:
            break
        url = f"https://aoe4world.com/api/v0/leaderboards/rm_solo?limit={batch_size}&offset={offset}"
        response = requests.get(url)
        if response.status_code != 200:
            continue
        data = response.json()
        batch = data.get('players', [])
        if not batch:
            break
        players.update([p['profile_id'] for p in batch])
    
    return list(players)[:limit]



# Get recent matches for a specific player
def get_all_matches_for_player(profile_id, max_matches):
    matches = []
    offset = 0
    batch_size = 100  # typical max per API request

    while len(matches) < max_matches:
        url = f"https://aoe4world.com/api/v0/players/{profile_id}/games?limit={batch_size}&offset={offset}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Error fetching matches for {profile_id} at offset {offset}: {response.status_code}")
            break

        data = response.json()
        new_matches = data.get('games', [])
        if not new_matches:
            break  # no more data available

        matches.extend(new_matches)
        offset += batch_size
        time.sleep(0.1)  # throttle

    return matches[:max_matches]


# Extract features from a match JSON object
def extract_features_from_match(match):
    if 'teams' not in match or len(match['teams']) != 2:
        return None  # Not a valid 1v1 or 2v2+

    try:
        team_A = match['teams'][0]
        team_B = match['teams'][1]
        
        team_size = len(team_A)

        def team_features(team):
            mmrs = [p['player'].get("mmr", 0) for p in team]
            civs = [p['player'].get("civilization", "Unknown") for p in team]
            return sum(mmrs) / len(mmrs), civs

        mmr_A, civs_A = team_features(team_A)
        mmr_B, civs_B = team_features(team_B)

        # Determine if team A won
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
        print("Error parsing match:", e)
        return None

# Aggregate dataset across many players
def build_dataset(player_ids, matches_per_player):
    data_1v1 = []
    data_team = []
    for pid in player_ids:
        print(f"Fetching matches for player {pid}...")
        matches = get_all_matches_for_player(pid, max_matches=matches_per_player)
        for match in matches:
            features = extract_features_from_match(match)
                
            if features:
                if features["team_size"] != 1:
                    data_team.append(features)
                else:
                    data_1v1.append(features)
        time.sleep(0.1)  # Be kind to the server
    return pd.DataFrame(data_1v1),pd.DataFrame(data_team)

    
# Main execution
if __name__ == "__main__":
    player_ids = get_leaderboard_players(limit=10)
    df_1v1, df_team = build_dataset(player_ids, matches_per_player=10)

    df_1v1.to_csv("aoe4_1v1_matches_random.csv", index=False)
    df_team.to_csv("aoe4_team_matches_random.csv", index=False)
    
    df_1v1 = pd.get_dummies(df_1v1, columns=['map_name'], prefix='map')
    df_team = pd.get_dummies(df_team, columns=['map_name'], prefix='map')

    print("Saved 1v1 matches:", len(df_1v1))
    print("Saved team matches:", len(df_team))
