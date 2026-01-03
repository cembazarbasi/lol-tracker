from flask import Flask, render_template
import requests
import urllib.parse
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION ---
API_KEY = "RGAPI-d7ef42a1-6b12-4cf1-9d5c-cec9a0932def" # Replace with your Key
REGION = "europe"  # For Account-V1
PLATFORM = "euw1"     # For League-V4
# List of profiles to track
TRACKED_PLAYERS = [
    {"name": "Seek Bromance", "tag": "ERAN"},
    {"name": "Tyler1", "tag": "NA1"},
    {"name": "Faker", "tag": "KR1"} # Note: You might need to change PLATFORM to 'kr' dynamically for cross-region tracking
]

class RiotAPI:
    def __init__(self, api_key, region, platform):
        self.api_key = api_key
        self.region = region
        self.platform = platform
        self.headers = {"X-Riot-Token": self.api_key}

    def get_data(self, game_name, tag_line):
        # 1. Get PUUID
        safe_name = urllib.parse.quote(game_name)
        safe_tag = urllib.parse.quote(tag_line)
        account_url = f"https://{self.region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{safe_name}/{safe_tag}"
        
        resp = requests.get(account_url, headers=self.headers)
        if resp.status_code != 200:
            print(f"Error fetching Account for {game_name}#{tag_line}: {resp.status_code} - {resp.text}")
            return None
        puuid = resp.json().get('puuid')

        # 2. Get Summoner ID
        summoner_url = f"https://{self.platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        resp = requests.get(summoner_url, headers=self.headers)
        if resp.status_code != 200:
            print(f"Error fetching Summoner for {game_name}#{tag_line}: {resp.status_code} - {resp.text}")
            return None
        summoner_id = resp.json().get('id')
        profile_icon_id = resp.json().get('profileIconId')

        # 3. Get League Entries
        league_url = f"https://{self.platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        resp = requests.get(league_url, headers=self.headers)
        if resp.status_code != 200:
            print(f"Error fetching League Data: {resp.status_code} - {resp.text}")
            entries = []
        else:
            entries = resp.json()

        # 4. Format Data
        data = {
            "name": game_name,
            "tag": tag_line,
            "icon": profile_icon_id,
            "solo": {"rank": "Unranked", "lp": 0, "wins": 0, "losses": 0, "wr": 0},
            "flex": {"rank": "Unranked", "lp": 0, "wins": 0, "losses": 0, "wr": 0}
        }

        for entry in entries:
            q_type = entry.get('queueType')
            tier = entry.get('tier')
            rank = entry.get('rank')
            lp = entry.get('leaguePoints')
            wins = entry.get('wins')
            losses = entry.get('losses')
            total = wins + losses
            wr = round((wins / total * 100), 1) if total > 0 else 0
            
            rank_str = f"{tier} {rank}"

            if q_type == "RANKED_SOLO_5x5":
                data["solo"] = {"rank": rank_str, "lp": lp, "wins": wins, "losses": losses, "wr": wr}
            elif q_type == "RANKED_FLEX_SR":
                data["flex"] = {"rank": rank_str, "lp": lp, "wins": wins, "losses": losses, "wr": wr}
        
        return data

api = RiotAPI(API_KEY, REGION, PLATFORM)

@app.route('/')
def index():
    player_data = []
    for player in TRACKED_PLAYERS:
        # Note: In a production app, you should handle rate limits and errors here
        try:
            p_info = api.get_data(player["name"], player["tag"])
            if p_info:
                player_data.append(p_info)
        except Exception as e:
            print(f"Error fetching {player['name']}: {e}")
            
    days_played = (datetime.now() - datetime(2012, 1, 1)).days
    return render_template('index.html', players=player_data, days_played=days_played)

if __name__ == '__main__':
    app.run(debug=True)
