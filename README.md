# YouTube Page Research

A small tool for finding a YouTube niche and tracking what's working. It pulls
real data from the official **YouTube Data API v3** and saves it as CSV files
you can open in Excel or Google Sheets, or upload to Claude for analysis.

You only need Python 3. There's nothing to install.

## 1. Get your API key (about 5 minutes, free)

1. Go to <https://console.cloud.google.com/> and sign in with your Google account.
2. Click the project dropdown at the top, then **New Project**. Name it something
   like `youtube-research` and click **Create**. Make sure it's selected.
3. Open **APIs & Services → Library**, search for **YouTube Data API v3**, and
   click **Enable**.
4. Open **APIs & Services → Credentials → Create credentials → API key**. Copy the key.
5. Recommended: click the new key and, under **API restrictions**, choose
   **Restrict key → YouTube Data API v3**, then save.
6. In this folder, copy `.env.example` to `.env` and paste your key:

   ```
   YOUTUBE_API_KEY=AIza...your key...
   ```

   `.env` is in `.gitignore`, so your key is never committed. Don't share it.

## 2. Run it

### Compare niches (start here)

```bash
python3 yt_research.py niche "budget travel" "home workouts" "ai tools for students"
```

For each phrase, the tool takes the 50 most-viewed videos from the last 90 days
and reports:

| Metric | What it tells you |
|---|---|
| **median views/day** | Demand: how much people watch this topic |
| **small-channel share** | Openness: how many top videos come from channels under 100K subscribers |
| **big-channel share** | Saturation: how many come from channels over 1M subscribers |
| **breakout videos** | Videos with more views than their channel has subscribers, from small channels. **This is the strongest signal that a newcomer can win here.** |
| **opportunity score** | A rough ranking that combines the numbers above |

Useful options:

```bash
--days 30            # only look at the last 30 days (fresher trends)
--region GB          # country (default US)
--language en        # prefer results in a language
--duration short     # short (<4 min), medium (4-20 min), long (>20 min)
--top 10             # show more videos per niche
```

### See what's trending in a country

```bash
python3 yt_research.py categories --region US     # list category IDs
python3 yt_research.py trending --region US --category 28
```

### Study competitor channels

```bash
python3 yt_research.py channel @somechannel @anotherchannel --recent 50
```

This shows subscribers, total views, average and median views of recent videos,
the share of recent uploads that are Shorts, and their best recent videos.

## 3. Analyze the results with Claude

See `research/capybluh-niche-report.md` for a worked example: a niche report on cute and weird animated character Shorts.

Every run saves CSV files in `output/`. Upload them to Claude and ask things like:

- *"Here's my niche summary. Rank these niches for a beginner who can post 2
  videos a week, without showing my face. Explain your reasoning."*
- *"Here are the breakout videos for 'budget travel'. What do the titles have in
  common? Give me 15 video ideas in the same pattern."*
- *"Here are 5 competitor channels. What are they not covering that viewers want?"*

## Quota (free usage limit)

Google gives you **10,000 units per day**, which resets at midnight Pacific Time.

| Command | Approximate cost |
|---|---|
| `niche` | ~102 units **per keyword**, so about 95 keywords a day |
| `trending` | ~2 units |
| `channel` | ~3 units per channel |
| `categories` | 1 unit |

## Limitations

- YouTube search returns at most 50 videos per keyword here, so treat this as a
  sample, not a census.
- Search volume (how many people *search* a term) is not in the API. Use
  Google Trends (set to **YouTube Search**) or vidIQ/TubeBuddy for that.
- Some channels hide their subscriber count. These show as `hidden` and are
  left out of the channel-size metrics.
