from plexapi.server import PlexServer
import random
import logging
import os

PLEX_URL = 'http://192.168.4.24:32400'
PLEX_TOKEN = 'gz7kamaEUpxWAvVmzS6u'

COLLECTIONS = ['Saturday Morning Cartoons', 'Saturday Morning Live Action']
TV_LIBRARY = 'TV Shows'
PLAYLIST_NAME = '📺 Saturday Morning'
MAX_DURATION_MINUTES = 180
MAX_EPISODE_LENGTH_MINUTES = 55

# Setup logging
log_path = os.path.expanduser('~/Documents/plex_playlist.log')
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    library = plex.library.section(TV_LIBRARY)

    # Gather cartoon and live-action shows separately
    cartoon_shows = library.search(collection='Saturday Morning Cartoons')
    live_action_shows = library.search(collection='Saturday Morning Live Action')

    playlist_items = []
    total_duration = 0.0

    # Select 1 random live-action episode first (≤ 55 min)
    selected_live_action_episode = None
    if live_action_shows:
        random.shuffle(live_action_shows)
        for show in live_action_shows:
            try:
                episodes = show.episodes()
                valid_episodes = [ep for ep in episodes if ep.duration and 10 <= (ep.duration / 60000.0) <= MAX_EPISODE_LENGTH_MINUTES]
                if valid_episodes:
                    episode = random.choice(valid_episodes)
                    duration = episode.duration / 60000.0
                    if duration <= MAX_DURATION_MINUTES:
                        selected_live_action_episode = episode
                        total_duration += duration
                        logging.info(f"Added live-action: {show.title} - {episode.title} ({duration:.1f} min)")
                        break
            except Exception as e:
                logging.error(f"Error processing live-action show '{show.title}': {e}")

    cartoon_items = []
    random.shuffle(cartoon_shows)
    for show in cartoon_shows:
        try:
            episodes = show.episodes()
            valid_episodes = [ep for ep in episodes if ep.duration and 10 <= (ep.duration / 60000.0) <= MAX_EPISODE_LENGTH_MINUTES]
            if not valid_episodes:
                logging.info(f"No valid episodes for {show.title}")
                continue
            random.shuffle(valid_episodes)
            for episode in valid_episodes:
                episode_duration = episode.duration / 60000.0
                if total_duration + episode_duration <= MAX_DURATION_MINUTES:
                    cartoon_items.append(episode)
                    total_duration += episode_duration
                    logging.info(f"Added cartoon: {show.title} - {episode.title} ({episode_duration:.1f} min)")
                    break
        except Exception as e:
            logging.error(f"Error processing cartoon show '{show.title}': {e}")

    # Ensure at least two cartoons are placed first
    if len(cartoon_items) >= 2:
        playlist_items = cartoon_items[:2]
        if selected_live_action_episode:
            playlist_items.append(selected_live_action_episode)
        playlist_items.extend(cartoon_items[2:])
    else:
        playlist_items = cartoon_items  # fallback if not enough cartoons
        if selected_live_action_episode:
            playlist_items.append(selected_live_action_episode)

    if not playlist_items:
        logging.warning("No episodes selected. Playlist not created.")
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

if __name__ == '__main__':
    main()