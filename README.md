<file name=0 path=/Users/mbecker/Documents/GitHub/SatAmPlex/README.md># SatAmPlex
![Python](https://img.shields.io/badge/python-3.10+-blue)

SatAmPlex is a command-line tool that creates a nostalgic "Saturday Morning Cartoons" playlist using your Plex library. It randomly selects a mix of cartoon and live-action episodes, adhering to time limits and configurable rules.

## Features

- Includes 1 live-action show per playlist (optional)
- Runtime-limited playlist (default: 180 minutes)
- Customizable collections and length constraints
- Supports exclusions and shuffle settings
- Remembers multipart episode arcs and continues them across runs
- Plex login via Device Auth (no token copy/paste)
- Cross-platform log and config storage
- Easily installable as a CLI tool

## Installation

```bash
pip3 install -e .
```

This installs the CLI command:

```bash
saturday-morning
```

## First-Time Setup

1. Copy and edit the provided `config.yaml` file.
2. Authenticate with Plex:

```bash
saturday-morning --auth
```

This will open a login code for `https://plex.tv/link` and save your token securely.

## Usage

```bash
saturday-morning --dry-run
```

### CLI Options

- `--auth`: Log in to Plex and save token
- `--logout`: Remove saved token
- `--dry-run`: Preview playlist without creating it
- `--max-duration 150`: Limit total playlist length (minutes)
- `--min-length 10`: Minimum episode length
- `--max-length 55`: Maximum episode length
- `--no-live`: Exclude live-action entry
- `--no-shuffle`: Keep selected order
- `--show-continuity`: Show currently tracked multipart episodes
- `--reset-continuity`: Clear saved multipart episode state

## Config File (`config.yaml`)

Place your `config.yaml` in the working directory or user's config path:

```yaml
plex:
  url: "http://192.168.4.24:32400"
  tv_library: "TV Shows"

playlist:
  name: "📺 Saturday Morning"
  max_duration: 180
  max_episode_length: 55
  min_episode_length: 10
  include_live_action: true
  collections:
    cartoons: "Saturday Morning Cartoons"
    live_action: "Saturday Morning Live Action"
  exclude_titles: []
  shuffle_order: true
```

## Continuity Tracking File (`continuity.json`)

This optional file is automatically created and updated to track multipart episodes across runs. It ensures that if a multi-part arc starts (like `"The Ultimate Doom (1)"`), the next part will be scheduled in a future playlist. The tracking is grouped by series title to avoid cross-show conflicts.

### Example

```json
{
  "Transformers": {
    "The Ultimate Doom": {
      "next_part": 2,
      "total_parts": 3
    }
  },
  "G.I. Joe": {
    "The M.A.S.S. Device": {
      "next_part": 4,
      "total_parts": 5
    }
  }
}
```

The script will prioritize `"next_part"` the next time it runs. When the final part of an arc is played, that arc is automatically removed from the file.

## License

MIT — © 2025 Mike Becker / ZentrixLabs
</file>
