import requests
import pandas as pd

def fetch_civ_matchups():
    url = "https://aoe4world.com/api/v0/stats/rm_solo/matchups"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error: Status code {response.status_code}")
        return pd.DataFrame()
    
    data = response.json()
    matchups = data.get('data', [])  # <-- Correct field name

    # Build DataFrame from matchups
    records = []
    for m in matchups:
        civ_a = m['civilization']
        civ_b = m['other_civilization']
        win_rate = m['win_rate']
        games = m['games_count']
        records.append({
            'civ_a': civ_a,
            'civ_b': civ_b,
            'win_rate': win_rate,
            'games_count': games
        })
    
    return pd.DataFrame(records)

# Run the fetch and show first few records
df_matchups = fetch_civ_matchups()
df_matchups.to_csv("1v1_matchups.csv", index=False)
print(df_matchups.head())
