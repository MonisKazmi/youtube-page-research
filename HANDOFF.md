# Handoff: Faceless Animated Character Channel (resume here)

> **For Claude:** this file summarizes a previous working session with the user. Read it fully, then read
> `research/capybluh-niche-report.md` and `research/video-ideas-and-characters.md` before doing anything.
> Continue from "Next steps" below. Ask the user which character duo they picked if they haven't said.

*Last updated: October 7, 2026*

## The project

The user wants to launch a **faceless YouTube channel and Facebook Page** of **cute, weird animated characters with sound effects and music**, aimed at **US, UK and Western audiences**. The benchmark channel is [@capybluh](https://www.youtube.com/@capybluh).

- GitHub repo: `moniskazmi/youtube-page-research`, branch `claude/blissful-fermat-9p2a59` (everything below is pushed there)
- No pull request has been opened (the user hasn't asked for one).

## User preferences and rules (important)

1. **Never use OpenArt** unless the user explicitly says so. It's reserved for a client of theirs ("Ben").
2. The user wants to use **Google Flow** to make the characters. Flow has no connector or API for Claude, so the agreed route is a **Gemini API key** (Imagen for images, Veo for video, the same models Flow uses), read from the environment variable **`GEMINI_API_KEY`**. The user said they added it, but it wasn't visible in the old session because environment variables only load when a session starts. **Check whether it's available now.**
3. Higgsfield is also connected in the cloud environment, but it costs credits. Ask before using it.
4. The YouTube Data API key is read from `YOUTUBE_API_KEY` (an environment variable, or `.env` next to `yt_research.py`). Never commit keys, and never ask the user to paste keys into chat.

## What's in the repo

| File | What it is |
|---|---|
| `yt_research.py` | A standard-library Python tool that uses the YouTube Data API v3. Commands: `niche`, `trending`, `channel`, `categories`. Saves CSVs to `output/` (git-ignored). See `README.md`. |
| `research/capybluh-niche-report.md` | The full niche report built on live API data: Capybluh analysis, format openness, competitors, production, US/UK targeting, Made-for-Kids risk, Facebook strategy, metrics, risks, and a 30-day plan |
| `research/video-ideas-and-characters.md` | 8 character duos (with concept sketches and Google Flow prompts), 30 video ideas, and a 2-week posting schedule |
| `research/characters/*.svg` | Hand-drawn SVG concept sketches of the 8 duos (placeholders until the real art is generated) |
| `output/*.csv` (in the zip only) | Raw API data from the research runs on October 6, 2026 |

## Key findings (from live YouTube API data, October 6, 2026)

- **Capybluh:** 4.24M subscribers, 5.3B views. Last 50 videos averaged **30.7M views** (median 19.7M), and 49 of 50 are 15–30 second Shorts. Posts about one every 1.6 days. The main character is a **Roblox-style "noob"**, with a capybara sidekick.
- **Its formats (median views):** "With mom vs With dad" 34M · "What parents see vs what I see" 27M (top: 202.6M) · "How X works" 25M (vending machine: 124M) · "X 2000 vs 2026 vs 2050" 15.6M · emotional skits get the most comments.
- It **reuses the exact same title** many times (14 of 50 are "What parents see vs what i see").
- **How open each format is to new channels** (US, Shorts, last 90 days):
  - "how it works animation": 78% small channels, 39/50 breakouts → **most open**
  - "2000 vs 2026 vs 2050": 38% small, 17 breakouts → open
  - "mom vs dad" and "parents see vs I see": ~330–390K median views/day, but 72% big channels → crowded
  - "capybara animation": low demand (the capybara isn't the draw)
- **Competitors:** Hawks RBX (3.2M), Robert Noob (3.7M), Keybee Animation, YourNoobDude, Junivo, and newcomers Glipz (started March 2026, 464M views), WhirrMimi (6 videos, one 27M hit) and RobloxArtSchool (100K in 5 months).
- **Strategy agreed:**
  - Build **original** cute-weird characters, not Roblox characters.
  - Launch with the "How X works" and "2000 vs 2026 vs 2050" formats, then add the mom/dad and parents formats.
  - Make about 1 in 5 videos emotional.
  - Tell stories from a teen or adult point of view to avoid a Made-for-Kids classification.
  - Use licensed sound effects and music only.
  - Cross-post to a Facebook Page as Reels and post weekly compilations.

## Character duos (pick one)

1. **Blip & Moss** ⭐ (recommended): a tiny chaotic mint bean + a giant sleepy moss creature
2. Nugget & Toastie: a blob kid + a stressed toast parent
3. Pip & Grandpa Gloop: a hyper pink slime + a confused old slime
4. **Fizz & Doc Waffles** ⭐ (recommended for "How X works"): a nervous frog + a mad raccoon inventor
5. Mochi & Brick: a soft, sensitive creature + a blocky, overconfident one
6. Lil Dumpling & Big Bun: bun siblings
7. Squeak & The Fridge Gremlin
8. Taco & Pickle: deadpan best friends

The full descriptions, signature sounds and per-character Google Flow / Imagen prompts (with a shared style line) are in `research/video-ideas-and-characters.md`.

## Next steps (where we stopped)

1. **The user picks a duo.** If they haven't, ask; recommend Blip & Moss or Fizz & Doc Waffles.
2. **Generate the character art with the Gemini API** (`GEMINI_API_KEY`), using the prompts in the ideas file:
   - each character on its own, then both together (banner and thumbnail)
   - a character sheet: front, side and back views plus 4–6 expressions
   - save PNGs to `research/characters/` and swap them in for the SVG sketches in the ideas file
   - Don't use OpenArt.
3. Write **full scripts with shot lists and sound-effect cues** for the first 14 Shorts (the schedule is in the ideas file).
4. Optional: generate short test clips with Veo (9:16) using the video prompt template.
5. Optional: re-run `yt_research.py` for the UK (`--region GB`) and refresh the data.

## Useful commands

```bash
python3 yt_research.py channel @capybluh --recent 50
python3 yt_research.py niche "how it works animation inside" "2000 vs 2026 vs 2050" "with mom vs with dad" --region US --duration short --days 90
python3 yt_research.py niche "how it works animation inside" "with mom vs with dad" --region GB --duration short
```
