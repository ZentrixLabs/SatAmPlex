

# SatAmPlex
![Python](https://img.shields.io/badge/python-3.10+-blue)

SatAmPlex is a command-line tool that creates a nostalgic "Saturday Morning Cartoons" playlist using your Plex library. It randomly selects a mix of cartoon and live-action episodes, adhering to time limits and configurable rules.

## Features

- Includes 1 live-action show per playlist (optional)
- Runtime-limited playlist (default: 180 minutes)
- Customizable collections and length constraints
- Supports exclusions and shuffle settings
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

## License

MIT — © 2025 Mike Becker / ZentrixLabs
