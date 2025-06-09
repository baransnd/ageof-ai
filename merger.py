import pandas as pd

# Load datasets
matches_df = pd.read_csv("aoe4_1v1_matches.csv")
matchups_df = pd.read_csv("1v1_matchups.csv")

min_games = matchups_df["games_count"].min()
max_games = matchups_df["games_count"].max()

matchups_df["certainty"] = (matchups_df["games_count"] - min_games) / (max_games - min_games)

matchups_df = matchups_df.drop(columns=["games_count"])

# After calculating 'certainty'
matches_df = matches_df.merge(
    matchups_df,
    left_on=["team_A_civs", "team_B_civs"],
    right_on=["civ_a", "civ_b"],
    how="left"
).rename(columns={
    "win_rate": "civ_A_vs_B_winrate",
    "certainty": "civ_A_vs_B_certainty"
}).drop(columns=["civ_a", "civ_b"])

matches_df["mmr_gap"] = matches_df["team_A_avg_mmr"] - matches_df["team_B_avg_mmr"]


matches_df.to_csv("final2.csv", index=False)