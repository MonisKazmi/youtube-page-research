#!/usr/bin/env python3
"""YouTube niche research tool, built on the official YouTube Data API v3.

Commands:
  niche       Compare keywords/niches: demand, competition, and breakout videos
  trending    What's trending right now in a country (optionally by category)
  channel     Stats and recent-video performance for specific channels
  categories  List video category IDs for a country (for `trending --category`)

Results are printed and saved as CSV files in ./output, ready to upload to
Claude for analysis. Uses only the Python standard library.

Run `python3 yt_research.py <command> --help` for options.
"""

import argparse
import csv
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_BASE = "https://www.googleapis.com/youtube/v3/"
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"

# A channel under this many subscribers counts as "small" when judging how
# open a niche is to newcomers.
SMALL_CHANNEL_SUBS = 100_000
# A channel over this many subscribers counts as "big" (dominant competitor).
BIG_CHANNEL_SUBS = 1_000_000
# YouTube Shorts can be up to 3 minutes long.
SHORTS_MAX_SECONDS = 180

# API quota cost per call (default daily quota is 10,000 units).
SEARCH_COST = 100


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------

def load_api_key():
    key = os.environ.get("YOUTUBE_API_KEY")
    env_file = SCRIPT_DIR / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("YOUTUBE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key or key == "paste-your-key-here":
        sys.exit(
            "No API key found. Put YOUTUBE_API_KEY=your-key in a .env file next "
            "to this script (see README.md), or set the YOUTUBE_API_KEY "
            "environment variable."
        )
    return key


def api_get(endpoint, key, **params):
    params = {k: v for k, v in params.items() if v is not None}
    params["key"] = key
    url = API_BASE + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e)["error"]
            reason = err.get("errors", [{}])[0].get("reason", "")
            message = err.get("message", str(e))
        except Exception:
            reason, message = "", str(e)
        if reason == "quotaExceeded":
            sys.exit(
                "YouTube API daily quota used up. It resets at midnight Pacific "
                "Time. Tip: use fewer keywords per run (each costs ~100 units)."
            )
        if reason in ("keyInvalid", "badRequest") and "API key" in message:
            sys.exit("Your API key was rejected. Check the key in your .env file.")
        sys.exit(f"YouTube API error ({e.code} {reason}): {message}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error talking to YouTube: {e.reason}")


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def fetch_videos(video_ids, key):
    videos = []
    for batch in chunks(list(dict.fromkeys(video_ids)), 50):
        data = api_get("videos", key, part="snippet,statistics,contentDetails",
                       id=",".join(batch), maxResults=50)
        videos.extend(data.get("items", []))
    return videos


def fetch_channels(channel_ids, key):
    channels = {}
    for batch in chunks(list(dict.fromkeys(channel_ids)), 50):
        data = api_get("channels", key, part="snippet,statistics,contentDetails",
                       id=",".join(batch), maxResults=50)
        for item in data.get("items", []):
            channels[item["id"]] = item
    return channels


# --------------------------------------------------------------------------
# Data shaping
# --------------------------------------------------------------------------

def parse_duration(iso):
    """Convert an ISO 8601 duration like PT1H2M3S to seconds."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def to_int(value):
    return int(value) if value is not None else None


def subscriber_count(channel):
    stats = (channel or {}).get("statistics", {})
    if stats.get("hiddenSubscriberCount"):
        return None
    return to_int(stats.get("subscriberCount"))


def build_rows(videos, channels, now):
    rows = []
    for v in videos:
        snip, stats = v["snippet"], v.get("statistics", {})
        published = datetime.fromisoformat(snip["publishedAt"].replace("Z", "+00:00"))
        age_days = max((now - published).total_seconds() / 86400, 1 / 24)
        views = to_int(stats.get("viewCount")) or 0
        subs = subscriber_count(channels.get(snip["channelId"]))
        seconds = parse_duration(v.get("contentDetails", {}).get("duration"))
        rows.append({
            "title": snip["title"],
            "channel": snip["channelTitle"],
            "subscribers": subs,
            "views": views,
            "likes": to_int(stats.get("likeCount")),
            "comments": to_int(stats.get("commentCount")),
            "published": published.strftime("%Y-%m-%d"),
            "age_days": round(age_days, 1),
            "views_per_day": round(views / age_days),
            "views_to_subs": round(views / subs, 2) if subs else None,
            "duration_min": round(seconds / 60, 1),
            "format": "short" if 0 < seconds <= SHORTS_MAX_SECONDS else "long",
            "url": f"https://www.youtube.com/watch?v={v['id']}",
        })
    return rows


def is_breakout(row):
    """A video that got more views than its channel has subscribers, from a
    channel that isn't already big: a sign the topic itself pulls viewers."""
    subs = row["subscribers"]
    return subs is not None and subs < SMALL_CHANNEL_SUBS and row["views"] >= subs


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------

def write_csv(name, rows):
    if not rows:
        return None
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = OUTPUT_DIR / f"{name}_{stamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def fmt_num(n):
    if n is None:
        return "hidden"
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= size:
            return f"{n / size:.1f}{unit}"
    return str(round(n))


def shorten(text, width):
    return text if len(text) <= width else text[: width - 1] + "…"


def print_video_table(rows, limit):
    print(f"  {'views':>7} {'views/day':>9} {'subs':>7}  {'fmt':5} title — channel")
    for r in rows[:limit]:
        print(f"  {fmt_num(r['views']):>7} {fmt_num(r['views_per_day']):>9} "
              f"{fmt_num(r['subscribers']):>7}  {r['format']:5} "
              f"{shorten(r['title'], 60)} — {shorten(r['channel'], 25)}")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_niche(args):
    key = load_api_key()
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Researching {len(args.keywords)} niche(s), videos from the last "
          f"{args.days} days (uses ~{len(args.keywords) * (SEARCH_COST + 2)} "
          f"of your 10,000 daily quota units)\n")

    all_rows, summaries = [], []
    for keyword in args.keywords:
        result = api_get("search", key, part="id", q=keyword, type="video",
                         order=args.order, publishedAfter=since, maxResults=50,
                         regionCode=args.region, relevanceLanguage=args.language,
                         videoDuration=args.duration)
        ids = [item["id"]["videoId"] for item in result.get("items", [])]
        if not ids:
            print(f"== {keyword}: no videos found\n")
            continue
        videos = fetch_videos(ids, key)
        channels = fetch_channels([v["snippet"]["channelId"] for v in videos], key)
        rows = build_rows(videos, channels, now)
        rows.sort(key=lambda r: r["views_per_day"], reverse=True)

        known = [r for r in rows if r["subscribers"] is not None]
        small = [r for r in known if r["subscribers"] < SMALL_CHANNEL_SUBS]
        big = [r for r in known if r["subscribers"] >= BIG_CHANNEL_SUBS]
        breakouts = [r for r in rows if is_breakout(r)]
        median_vpd = statistics.median(r["views_per_day"] for r in rows)
        small_share = len(small) / len(known) if known else 0

        summary = {
            "keyword": keyword,
            "videos_analyzed": len(rows),
            "median_views": round(statistics.median(r["views"] for r in rows)),
            "median_views_per_day": round(median_vpd),
            "small_channel_share": round(small_share, 2),
            "big_channel_share": round(len(big) / len(known), 2) if known else 0,
            "breakout_videos": len(breakouts),
            "shorts_share": round(sum(r["format"] == "short" for r in rows) / len(rows), 2),
            "unique_channels": len({r["channel"] for r in rows}),
            # Rough heuristic: demand (views/day) weighted by how much of the
            # results come from small channels, plus a bonus for breakouts.
            "opportunity_score": round(median_vpd * small_share * (1 + len(breakouts) / len(rows))),
        }
        summaries.append(summary)
        for r in rows:
            all_rows.append({"keyword": keyword, "breakout": is_breakout(r), **r})

        print(f"== {keyword}")
        print(f"  median views/day {fmt_num(summary['median_views_per_day'])} | "
              f"small-channel share {small_share:.0%} | "
              f"big-channel share {summary['big_channel_share']:.0%} | "
              f"breakouts {len(breakouts)}/{len(rows)}")
        if breakouts:
            print("  Breakout videos (more views than the channel has subscribers):")
            print_video_table(breakouts, args.top)
        else:
            print("  Top videos by views/day:")
            print_video_table(rows, args.top)
        print()

    if not summaries:
        return
    summaries.sort(key=lambda s: s["opportunity_score"], reverse=True)
    print("== Ranking (higher opportunity score = more demand and more room for small channels)")
    for i, s in enumerate(summaries, 1):
        print(f"  {i}. {s['keyword']:<35} score {fmt_num(s['opportunity_score']):>7}  "
              f"median views/day {fmt_num(s['median_views_per_day']):>7}  "
              f"small-channel share {s['small_channel_share']:.0%}")
    print()
    for label, path in (("Summary", write_csv("niche_summary", summaries)),
                        ("All videos", write_csv("niche_videos", all_rows))):
        print(f"{label} saved to {path.relative_to(SCRIPT_DIR)}")


def cmd_trending(args):
    key = load_api_key()
    now = datetime.now(timezone.utc)
    data = api_get("videos", key, part="snippet,statistics,contentDetails",
                   chart="mostPopular", regionCode=args.region,
                   videoCategoryId=args.category, maxResults=50)
    videos = data.get("items", [])
    if not videos:
        sys.exit("No trending videos returned (some categories have no chart in some countries).")
    channels = fetch_channels([v["snippet"]["channelId"] for v in videos], key)
    rows = build_rows(videos, channels, now)
    for rank, (row, video) in enumerate(zip(rows, videos), 1):
        row["trending_rank"] = rank
        row["category_id"] = video["snippet"].get("categoryId")
        row["tags"] = ", ".join(video["snippet"].get("tags", [])[:10])
    label = f"category {args.category}" if args.category else "all categories"
    print(f"Trending in {args.region} ({label}):\n")
    print_video_table(rows, args.top)
    print(f"\nSaved to {write_csv(f'trending_{args.region}', rows).relative_to(SCRIPT_DIR)}")


def resolve_channel(ref, key):
    if ref.startswith("UC") and len(ref) == 24:
        params = {"id": ref}
    else:
        params = {"forHandle": ref if ref.startswith("@") else "@" + ref}
    data = api_get("channels", key, part="snippet,statistics,contentDetails", **params)
    items = data.get("items", [])
    return items[0] if items else None


def cmd_channel(args):
    key = load_api_key()
    now = datetime.now(timezone.utc)
    summaries, all_rows = [], []
    for ref in args.channels:
        channel = resolve_channel(ref, key)
        if not channel:
            print(f"== {ref}: channel not found (use the @handle or the UC... channel ID)\n")
            continue
        uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        playlist = api_get("playlistItems", key, part="contentDetails",
                           playlistId=uploads, maxResults=min(args.recent, 50))
        ids = [i["contentDetails"]["videoId"] for i in playlist.get("items", [])]
        rows = build_rows(fetch_videos(ids, key), {channel["id"]: channel}, now)
        stats = channel["statistics"]
        name = channel["snippet"]["title"]
        avg_views = round(statistics.mean(r["views"] for r in rows)) if rows else 0
        summary = {
            "channel": name,
            "handle": channel["snippet"].get("customUrl", ""),
            "subscribers": subscriber_count(channel),
            "total_views": to_int(stats.get("viewCount")),
            "video_count": to_int(stats.get("videoCount")),
            "created": channel["snippet"]["publishedAt"][:10],
            "recent_videos": len(rows),
            "recent_avg_views": avg_views,
            "recent_median_views": round(statistics.median(r["views"] for r in rows)) if rows else 0,
            "recent_shorts_share": round(sum(r["format"] == "short" for r in rows) / len(rows), 2) if rows else 0,
        }
        summaries.append(summary)
        all_rows.extend(rows)

        print(f"== {name} ({summary['handle']})")
        print(f"  {fmt_num(summary['subscribers'])} subscribers | "
              f"{fmt_num(summary['total_views'])} total views | "
              f"{summary['video_count']} videos | since {summary['created']}")
        print(f"  Last {len(rows)} videos: avg {fmt_num(avg_views)} views, "
              f"median {fmt_num(summary['recent_median_views'])}")
        print("  Best recent videos:")
        print_video_table(sorted(rows, key=lambda r: r["views"], reverse=True), args.top)
        print()

    if summaries:
        print(f"Channels saved to {write_csv('channels', summaries).relative_to(SCRIPT_DIR)}")
        if all_rows:
            print(f"Videos saved to {write_csv('channel_videos', all_rows).relative_to(SCRIPT_DIR)}")


def cmd_categories(args):
    key = load_api_key()
    data = api_get("videoCategories", key, part="snippet", regionCode=args.region)
    print(f"Video categories in {args.region} (use the ID with `trending --category`):")
    for item in data.get("items", []):
        if item["snippet"].get("assignable"):
            print(f"  {item['id']:>3}  {item['snippet']['title']}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="YouTube niche research using the YouTube Data API v3.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            '  python3 yt_research.py niche "budget travel" "home workouts" "ai tools"\n'
            "  python3 yt_research.py trending --region US --category 28\n"
            "  python3 yt_research.py channel @mkbhd @aliabdaal\n"
            "  python3 yt_research.py categories --region GB"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("niche", help="compare niches/keywords for demand and competition")
    p.add_argument("keywords", nargs="+", help='one or more search phrases, quoted, e.g. "budget travel"')
    p.add_argument("--days", type=int, default=90, help="only videos published in the last N days (default 90)")
    p.add_argument("--region", default="US", help="2-letter country code (default US)")
    p.add_argument("--language", help="prefer results in this language, e.g. en, es, hi")
    p.add_argument("--order", default="viewCount", choices=["viewCount", "relevance", "date", "rating"],
                   help="how YouTube ranks the 50 results it returns (default viewCount)")
    p.add_argument("--duration", choices=["short", "medium", "long"],
                   help="short (<4 min), medium (4-20 min), long (>20 min)")
    p.add_argument("--top", type=int, default=5, help="videos to show per niche (default 5)")
    p.set_defaults(func=cmd_niche)

    p = sub.add_parser("trending", help="most popular videos right now in a country")
    p.add_argument("--region", default="US", help="2-letter country code (default US)")
    p.add_argument("--category", help="category ID (see the `categories` command)")
    p.add_argument("--top", type=int, default=20, help="videos to show (default 20)")
    p.set_defaults(func=cmd_trending)

    p = sub.add_parser("channel", help="stats for specific channels (competitor research)")
    p.add_argument("channels", nargs="+", help="@handles or UC... channel IDs")
    p.add_argument("--recent", type=int, default=30, help="recent videos to analyze, max 50 (default 30)")
    p.add_argument("--top", type=int, default=5, help="best videos to show per channel (default 5)")
    p.set_defaults(func=cmd_channel)

    p = sub.add_parser("categories", help="list video category IDs for a country")
    p.add_argument("--region", default="US", help="2-letter country code (default US)")
    p.set_defaults(func=cmd_categories)

    args = parser.parse_args()
    if getattr(args, "region", None):
        args.region = args.region.upper()
    args.func(args)


if __name__ == "__main__":
    main()
