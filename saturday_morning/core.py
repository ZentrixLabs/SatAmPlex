from plexapi.server import PlexServer
import random
import logging
import os
import yaml
import argparse
from platformdirs import PlatformDirs
from datetime import datetime
import re
import requests
import time
import json

CONFIG_PATH = os.path.expanduser('config.yaml')
try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
except Exception as e:
    print(f"Error loading config: {e}")
    exit(1)

dirs = PlatformDirs("SaturdayAmPlex", "ZentrixLabs")
token_path = os.path.join(dirs.user_config_path, "token.json")

continuity_path = os.path.join(dirs.user_config_path, "continuity.json")

def load_continuity():
    if os.path.exists(continuity_path):
        with open(continuity_path, 'r') as f:
            return json.load(f)
    return {}

def save_continuity(data):
    os.makedirs(os.path.dirname(continuity_path), exist_ok=True)
    with open(continuity_path, 'w') as f:
        json.dump(data, f, indent=2)

PLEX_URL = config['plex']['url']

def load_plex_token_or_exit():
    token = config['plex'].get('token')
    if not token and os.path.exists(token_path):
        with open(token_path, 'r') as f:
            token = json.load(f).get("token")
    if not token:
        print("❌ No Plex token found. Please run with --auth to log in.")
        exit(1)
    return token

TV_LIBRARY = config['plex']['tv_library']

COLLECTIONS = [
    config['playlist']['collections']['cartoons'],
    config['playlist']['collections']['live_action']
]
PLAYLIST_NAME = config['playlist']['name']
MAX_DURATION_MINUTES = config['playlist']['max_duration']
MAX_EPISODE_LENGTH_MINUTES = config['playlist']['max_episode_length']

MIN_EPISODE_LENGTH_MINUTES = config['playlist'].get('min_episode_length', 10)
INCLUDE_LIVE_ACTION = config['playlist'].get('include_live_action', True)
EXCLUDE_TITLES = [t.lower() for t in config['playlist'].get('exclude_titles', [])]
SHUFFLE_ORDER = config['playlist'].get('shuffle_order', True)

log_dir = dirs.user_log_path
os.makedirs(log_dir, exist_ok=True)
emoji_pattern = re.compile("["
    u"\U0001F600-\U0001F64F"  # emoticons
    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    u"\U0001F680-\U0001F6FF"  # transport & map symbols
    u"\U0001F1E0-\U0001F1FF"  # flags
    u"\U00002700-\U000027BF"  # dingbats
    u"\U000024C2-\U0001F251"  # enclosed characters
    "]+", flags=re.UNICODE)
clean_name = emoji_pattern.sub('', PLAYLIST_NAME)
safe_name = "".join(c if c.isalnum() else "_" for c in clean_name)
date_str = datetime.now().strftime("%Y-%m-%d")
log_filename = f"{safe_name}_{date_str}.log"
log_path = os.path.join(log_dir, log_filename)
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def authenticate_and_save_token():
    client_id = "SaturdayAmPlex"
    headers = {
        "X-Plex-Client-Identifier": client_id,
        "X-Plex-Product": "SaturdayAmPlex",
        "X-Plex-Version": "1.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print("🔐 Requesting device code from Plex...")
    res = requests.post("https://plex.tv/api/v2/pins", headers=headers)
    try:
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print("❌ Failed to parse Plex response:")
        print(f"Status Code: {res.status_code}")
        print(f"Response Text: {res.text}")
        raise
    # data = res.json()
    pin_id = data["id"]
    code = data["code"]

    print(f"👉 Visit https://plex.tv/link and enter the code: {code}")
    print("⏳ Waiting for you to complete the login...")

    for _ in range(60):
        time.sleep(2)
        poll = requests.get(f"https://plex.tv/api/v2/pins/{pin_id}", headers=headers)
        poll.raise_for_status()
        auth = poll.json().get("authToken")
        if auth:
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, "w") as f:
                json.dump({"token": auth}, f)
            print("✅ Login successful! Token saved.")
            try:
                plex = PlexServer(PLEX_URL, auth)
                user = plex.myPlexAccount()
                print(f"🔓 Logged in as: {user.username}")
            except Exception:
                print("⚠️ Login succeeded but user info could not be retrieved.")
            return auth

    print("❌ Login timed out.")
    return None

def parse_multipart_title(title):
    # Look for something like: Title: Subtitle (1)
    match = re.search(r"^(.*?)(?:[:\-]\s*.*?)?\s*\((\d+)\)", title)
    if match:
        base = match.group(1).strip()
        part = int(match.group(2))
        return base, part
    return None, None

def main(dry_run=False, max_duration=None, min_length=None, max_length=None, no_live=False, no_shuffle=False):
    PLEX_TOKEN = load_plex_token_or_exit()
    max_duration = max_duration or MAX_DURATION_MINUTES
    min_length = min_length or MIN_EPISODE_LENGTH_MINUTES
    max_length = max_length or MAX_EPISODE_LENGTH_MINUTES
    include_live = not no_live and INCLUDE_LIVE_ACTION
    shuffle_order = not no_shuffle and SHUFFLE_ORDER

    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    try:
        user = plex.myPlexAccount()
        print(f"🔓 Logged in as: {user.username}")
    except Exception:
        print("⚠️ Could not retrieve logged in user info.")
    library = plex.library.section(TV_LIBRARY)

    # Gather cartoon and live-action shows separately
    cartoon_shows = library.search(collection=config['playlist']['collections']['cartoons'])
    live_action_shows = library.search(collection=config['playlist']['collections']['live_action'])

    playlist_items = []
    total_duration = 0.0

    continuity = load_continuity()

    # Try to continue any multipart arc in progress
    continuing_ep = None
    for show in cartoon_shows:
        try:
            episodes = show.episodes()
            for ep in episodes:
                base, part = parse_multipart_title(ep.title)
                if base and show.title in continuity and base in continuity[show.title] and continuity[show.title][base]["next_part"] == part:
                    ep_duration = ep.duration / 60000.0
                    if min_length <= ep_duration <= max_length and total_duration + ep_duration <= max_duration:
                        continuing_ep = ep
                        total_duration += ep_duration
                        logging.info(f"Continuing multipart: {show.title} - {ep.title} ({ep_duration:.1f} min)")
                        break
            if continuing_ep:
                playlist_items.append(continuing_ep)
                break
        except Exception as e:
            logging.error(f"Error checking continuity for show '{show.title}': {e}")

    # Select 1 random live-action episode first (≤ 55 min)
    selected_live_action_episode = None
    if include_live:
        if live_action_shows:
            random.shuffle(live_action_shows)
            for show in live_action_shows:
                if show.title.lower() in EXCLUDE_TITLES:
                    logging.info(f"Skipped excluded show: {show.title}")
                    continue
                try:
                    episodes = show.episodes()
                    valid_episodes = [ep for ep in episodes if ep.duration and min_length <= (ep.duration / 60000.0) <= max_length]
                    if valid_episodes:
                        episode = random.choice(valid_episodes)
                        duration = episode.duration / 60000.0
                        if duration <= max_duration:
                            selected_live_action_episode = episode
                            total_duration += duration
                            logging.info(f"Added live-action: {show.title} - {episode.title} ({duration:.1f} min)")
                            break
                except Exception as e:
                    logging.error(f"Error processing live-action show '{show.title}': {e}")

    cartoon_items = []
    random.shuffle(cartoon_shows)
    added_series = set()
    for show in cartoon_shows:
        if show.title.lower() in EXCLUDE_TITLES:
            logging.info(f"Skipped excluded show: {show.title}")
            continue
        if show.title in added_series:
            continue
        try:
            episodes = show.episodes()
            valid_episodes = [ep for ep in episodes if ep.duration and min_length <= (ep.duration / 60000.0) <= max_length]
            if not valid_episodes:
                logging.info(f"No valid episodes for {show.title}")
                continue
            random.shuffle(valid_episodes)
            for episode in valid_episodes:
                base, part = parse_multipart_title(episode.title)
                if part and part > 1:
                    if show.title not in continuity or base not in continuity[show.title] or continuity[show.title][base]["next_part"] != part:
                        continue  # Skip if it's part 2+ and not the expected one
                episode_duration = episode.duration / 60000.0
                if total_duration + episode_duration <= max_duration:
                    cartoon_items.append(episode)
                    total_duration += episode_duration
                    logging.info(f"Added cartoon: {show.title} - {episode.title} ({episode_duration:.1f} min)")
                    added_series.add(show.title)
                    if base and part:
                        if show.title not in continuity:
                            continuity[show.title] = {}
                        continuity[show.title][base] = {
                            "next_part": part + 1,
                            "total_parts": continuity[show.title].get(base, {}).get("total_parts", part + 1)
                        }
                        # Cleanup: remove completed arcs from continuity
                        if continuity[show.title][base]["next_part"] > continuity[show.title][base]["total_parts"]:
                            del continuity[show.title][base]
                            if not continuity[show.title]:
                                del continuity[show.title]
                    break
        except Exception as e:
            logging.error(f"Error processing cartoon show '{show.title}': {e}")

    # Ensure at least two cartoons are placed first
    if len(cartoon_items) >= 2:
        playlist_items.extend(cartoon_items[:2])
        if selected_live_action_episode:
            playlist_items.append(selected_live_action_episode)
        playlist_items.extend(cartoon_items[2:])
    else:
        playlist_items.extend(cartoon_items)  # fallback if not enough cartoons
        if selected_live_action_episode:
            playlist_items.append(selected_live_action_episode)

    if not playlist_items:
        logging.warning("No episodes selected. Playlist not created.")
        return

    if shuffle_order:
        random.shuffle(playlist_items)

    def is_live_action(ep):
        return ep.librarySectionTitle.lower() == config['playlist']['collections']['live_action'].lower()

    if playlist_items and is_live_action(playlist_items[0]):
        for i in range(1, len(playlist_items)):
            if not is_live_action(playlist_items[i]):
                playlist_items[0], playlist_items[i] = playlist_items[i], playlist_items[0]
                break

    if dry_run:
        print(f"DRY RUN: Would create playlist '{PLAYLIST_NAME}' with:")
        for ep in playlist_items:
            print(f"- {ep.grandparentTitle} - {ep.title} ({ep.duration / 60000.0:.1f} min)")
        return

    # Delete old playlist if exists
    try:
        existing = plex.playlist(PLAYLIST_NAME)
        existing.delete()
        logging.info(f"Deleted old playlist '{PLAYLIST_NAME}'")
    except:
        pass  # No existing playlist

    # Create new playlist
    plex.createPlaylist(PLAYLIST_NAME, items=playlist_items)
    logging.info(f"Created playlist '{PLAYLIST_NAME}' with {len(playlist_items)} episodes, total duration {total_duration:.1f} min")

    save_continuity(continuity)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate a Saturday Morning playlist.")
    parser.add_argument('--dry-run', action='store_true', help="Print selected episodes without creating playlist")
    parser.add_argument('--auth', action='store_true', help="Login to Plex and store token")
    parser.add_argument('--logout', action='store_true', help="Logout and remove saved token")
    parser.add_argument('--max-duration', type=int, help="Override max total duration in minutes")
    parser.add_argument('--min-length', type=int, help="Override minimum episode length in minutes")
    parser.add_argument('--max-length', type=int, help="Override maximum episode length in minutes")
    parser.add_argument('--no-live', action='store_true', help="Exclude live action segment")
    parser.add_argument('--no-shuffle', action='store_true', help="Disable shuffling of playlist order")
    parser.add_argument('--reset-continuity', action='store_true', help="Clear continuity tracking data")
    parser.add_argument('--show-continuity', action='store_true', help="Print current continuity tracking data")
    args = parser.parse_args()
    if args.logout:
        if os.path.exists(token_path):
            os.remove(token_path)
            print("🚪 Logged out: saved token removed.")
        else:
            print("ℹ️ No saved token to delete.")
        exit()
    if args.reset_continuity:
        save_continuity({})
        print("🧹 Continuity data reset.")
        exit()
    if args.show_continuity:
        continuity = load_continuity()
        if not continuity:
            print("📭 No continuity data found.")
        else:
            print("📺 Current continuity tracking:")
            for series, arcs in continuity.items():
                print(f"{series}:")
                for arc, data in arcs.items():
                    print(f"  - {arc}: Next Part {data['next_part']} of {data['total_parts']}")
        exit()
    if args.auth:
        authenticate_and_save_token()
    else:
        main(
            dry_run=args.dry_run,
            max_duration=args.max_duration,
            min_length=args.min_length,
            max_length=args.max_length,
            no_live=args.no_live,
            no_shuffle=args.no_shuffle
        )