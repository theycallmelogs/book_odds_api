"""Pull FanDuel NBA player-prop alt lines from The Odds API and save them for the NBA Alt Line Board.

Runs in GitHub Actions (see .github/workflows/fd-odds.yml). Standard library only.

Env:
  ODDS_API_KEY   your The Odds API key (store it as a GitHub Actions secret, never in the repo)
  HOURS_AHEAD    only price games starting within this many hours (default 30)
  MARKETS        comma list of markets (default: the five alt markets the Board uses)
  ODDS_API_BASE  override the API host (testing only)

Cost: each game costs one credit per market (FanDuel only = one region).
With the default five markets, a 14-game slate costs 70 credits. Listing games is free.

Output (committed by the workflow):
  odds/fd_YYYY-MM-DD.txt   one line per leg:  YYYY-MM-DD, Player Name, STAT, N+, odds
  odds/latest.txt          everything from this run
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KEY = os.environ.get('ODDS_API_KEY', '').strip()
BASE = os.environ.get('ODDS_API_BASE', 'https://api.the-odds-api.com').rstrip('/')
HOURS = float(os.environ.get('HOURS_AHEAD', '30'))
MARKETS = os.environ.get('MARKETS', 'player_points_alternate,player_rebounds_alternate,player_assists_alternate,'
                                    'player_threes_alternate,player_points_rebounds_assists_alternate')
STAT = {
    'player_points': 'PTS', 'player_points_alternate': 'PTS',
    'player_rebounds': 'REB', 'player_rebounds_alternate': 'REB',
    'player_assists': 'AST', 'player_assists_alternate': 'AST',
    'player_threes': '3PM', 'player_threes_alternate': '3PM',
    'player_points_rebounds_assists': 'PRA', 'player_points_rebounds_assists_alternate': 'PRA',
}
CT = ZoneInfo('America/Chicago')
if not KEY:
    sys.exit('ODDS_API_KEY is not set. Add it under Settings > Secrets and variables > Actions.')


def get(path, **params):
    params['apiKey'] = KEY
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'nba-alt-line-board/1.0'})
    with urllib.request.urlopen(req, timeout=40) as r:
        left = r.headers.get('x-requests-remaining')
        return json.loads(r.read().decode()), left


now = datetime.now(timezone.utc)
events, _ = get('/v4/sports/basketball_nba/events',
                commenceTimeFrom=now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                commenceTimeTo=(now + timedelta(hours=HOURS)).strftime('%Y-%m-%dT%H:%M:%SZ'))
print(f"{len(events)} NBA games in the next {HOURS:g} hours (listing games is free)")

legs, left = {}, None
for ev in events:
    date = datetime.fromisoformat(ev['commence_time'].replace('Z', '+00:00')).astimezone(CT).strftime('%Y-%m-%d')
    try:
        data, left = get(f"/v4/sports/basketball_nba/events/{ev['id']}/odds",
                         bookmakers='fanduel', markets=MARKETS, oddsFormat='american')
    except Exception as e:  # one bad game shouldn't sink the run
        print(f"  {ev.get('away_team')} @ {ev.get('home_team')}: failed ({e})")
        continue
    n = 0
    for bk in data.get('bookmakers', []):
        if bk.get('key') != 'fanduel':
            continue
        for m in bk.get('markets', []):
            stat = STAT.get(m.get('key'))
            if not stat:
                continue
            for o in m.get('outcomes', []):
                name, player, point, price = o.get('name', ''), o.get('description'), o.get('point'), o.get('price')
                if not player or price is None or point is None:
                    continue
                if name.lower() not in ('over', 'yes'):
                    continue  # unders are not used by the Board
                if abs(float(point) % 1 - 0.5) > 1e-9:
                    continue  # X+ milestones arrive as Over (X - 0.5)
                N = int(float(point) + 0.5)
                key = (date, player, stat, N)
                if key not in legs or price > legs[key]:
                    legs[key] = int(price)
                n += 1
    print(f"  {ev.get('away_team')} @ {ev.get('home_team')}: {n} FanDuel lines")

os.makedirs('odds', exist_ok=True)
stamp = datetime.now(CT).strftime('%b %-d, %-I:%M %p CT')
rows = sorted(legs.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3]))
fmt = lambda k, v: f"{k[0]}, {k[1]}, {k[2]}, {k[3]}+, {'+' if v > 0 else ''}{v}"
header = f"# FanDuel NBA odds via The Odds API, pulled {stamp}, {len(rows)} legs from {len(events)} games"
with open('odds/latest.txt', 'w') as f:
    f.write(header + '\n' + '\n'.join(fmt(k, v) for k, v in rows) + '\n')
for d in sorted({k[0] for k in legs}):
    with open(f'odds/fd_{d}.txt', 'w') as f:
        part = [fmt(k, v) for k, v in rows if k[0] == d]
        f.write(f"{header}\n" + '\n'.join(part) + '\n')
print(f"Saved {len(rows)} legs. Credits remaining: {left}")
