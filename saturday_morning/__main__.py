import argparse
from saturday_morning import main, authenticate_and_save_token, token_path
import os

def cli_entry():
    parser = argparse.ArgumentParser(description="Generate a Saturday Morning playlist.")
    parser.add_argument('--dry-run', action='store_true', help="Print selected episodes without creating playlist")
    parser.add_argument('--auth', action='store_true', help="Login to Plex and store token")
    parser.add_argument('--logout', action='store_true', help="Logout and remove saved token")
    parser.add_argument('--max-duration', type=int)
    parser.add_argument('--min-length', type=int)
    parser.add_argument('--max-length', type=int)
    parser.add_argument('--no-live', action='store_true')
    parser.add_argument('--no-shuffle', action='store_true')

    args = parser.parse_args()

    if args.logout:
        if os.path.exists(token_path):
            os.remove(token_path)
            print("🚪 Logged out: saved token removed.")
        else:
            print("ℹ️ No saved token to delete.")
        return

    if args.auth:
        authenticate_and_save_token()
        return

    main(
        dry_run=args.dry_run,
        max_duration=args.max_duration,
        min_length=args.min_length,
        max_length=args.max_length,
        no_live=args.no_live,
        no_shuffle=args.no_shuffle,
    )