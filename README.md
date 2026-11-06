# FanDuel odds feed for the NBA Alt Line Board

A GitHub Action pulls FanDuel's NBA alt lines (points, rebounds, assists, threes, PRA, including the X+ milestone lines) from The Odds API and saves them in this repo. Claude reads them from here and loads them into the Board.

## Setup (about 10 minutes, once)

1. **Get a key.** Sign up at https://the-odds-api.com (the free Starter plan needs no card). Copy your API key. Don't paste it in chat or into any file.
2. **Create a repo.** On GitHub, create a new **public** repository, for example `nba-fd-odds`. Public lets Claude read the odds files; your key stays private in step 4.
3. **Add the two files.** Use *Add file > Create new file* for each one and paste its contents:
   - `fetch_fd_odds.py`
   - `.github/workflows/fd-odds.yml` (type the whole path, including the folders)
4. **Store the key.** Settings > Secrets and variables > Actions > New repository secret. Name: `ODDS_API_KEY`. Value: your key.
5. **Test it.** Actions tab > enable workflows if asked > *FanDuel NBA odds* > *Run workflow*. When it finishes, the repo has an `odds/latest.txt` file.
6. **Tell Claude the repo name** (for example `yourname/nba-fd-odds`).

## When it runs

- Every day at 4:30 PM Chicago time, after FanDuel posts its alt ladders. Edit the `cron` line to change it (times are UTC: 22:30 UTC = 4:30 PM CST).
- Any time you click *Run workflow*.

## Cost

Each game costs one credit per market. The five default markets = 5 credits per game, so a 14-game slate is about 70 credits. Listing games is free. The free plan's 500 credits a month covers about seven slates at one pull each; the run log prints the credits you have left.
