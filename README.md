# Mashiro

A multi-purpose Discord bot for personal use. It combines a fully featured music player, an in-character AI chatbot, a media downloader, and a handful of server-utility commands.

## Features

### 🎵 Music player

- `/play [URL/keyword]` — play audio from a URL or by searching YouTube. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp), so YouTube, Niconico, SoundCloud, BiliBili and [many other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) are supported.
- `/play-file` — upload a local audio/video file and play it.
- `/play-channel` — collect links posted in a given channel and queue them as a playlist.
- `/search` — browse YouTube search results and pick a track to play.
- Queue management: `/queue`, `/clear`, `/shuffle`, `/repeat`.
- Playback control: `/pause`, `/resume`, `/stop`, `/skip`, `/replay`, `/volume`, plus an interactive player message and `/player` to move it.
- `/connect` / `/disconnect` to manage the voice connection, and `/voice` to hear Mashiro speak.

### 💬 AI chatbot

Mention the bot or DM it to chat with Mashiro in character. Responses are generated with Google **Gemini 1.5 Pro** on whitelisted guilds, falling back to a free GPT-4o-mini backend ([g4f](https://github.com/xtekky/gpt4free)) elsewhere. Conversations are kept per-channel and expire after inactivity; reset them with `/reset-conversation`. The model can also trigger actions inline — e.g. start playing a requested song or send a selfie.

### ⬇️ Media downloader

- `/dl video` / `/dl audio` — get a direct download link for a video or its audio (also available as message context-menu commands).

### 🔗 URL replacement

- `/replace-url vxtwitter` — auto-convert X (Twitter) links to `vxtwitter.com` for rich embeds.
- `/replace-url phixiv` — auto-convert Pixiv links to `phixiv.net`.

### 🛠️ Server utilities

- `/send-message` — schedule a message to be sent at a specific date/time.
- `/nick change` / `/nick restore` / `/nick remove` — bulk-manage member nicknames (admin only).
- `/vc stats` — show information about your current voice channel; `/vc kick-timer` — auto-disconnect yourself after a set duration.
- `/kotobagari` — toggle word-filtering in the current channel (admin only).
- `/mashiro` — get a random character quote.
- `/ping`, `/help`.

Run `/help` in Discord for the full, up-to-date command list.

## How to Install

Click the [link](https://discord.com/api/oauth2/authorize?client_id=1105880759857860709&permissions=48794539912272&scope=applications.commands+bot) to install the bot on your guilds.

## Tech stack

- **Python 3.10**
- [Pycord](https://docs.pycord.dev/) for the Discord API
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) + **FFmpeg** for media
- [google-generativeai](https://github.com/google-gemini/generative-ai-python) / [g4f](https://github.com/xtekky/gpt4free) for chat
- Docker for deployment

## Setup

### Prerequisites

- Python 3.10+ and FFmpeg installed (the provided Docker image bundles FFmpeg for you).
- A Discord bot token with the necessary intents enabled.

### Environment variables

Create a `.env` file in the project root:

```env
DISCORD_BOT_TOKEN=your-discord-bot-token
GOOGLE_API_KEY=your-google-generative-ai-key   # optional; required only for Gemini-backed chat
```

### Run with Docker

The bot runs alongside a [PO Token provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) so that YouTube playback works from datacenter/VPS IPs (otherwise YouTube responds with "Sign in to confirm you're not a bot"). Use Docker Compose to start both services:

```bash
docker compose up -d --build
```

#### YouTube cookies (recommended)

For age-restricted videos or when the PO Token alone is not enough, place a `cookies.txt` (Netscape format, exported from a logged-in browser via an extension such as "Get cookies.txt LOCALLY") in the project root. It is auto-detected and mounted by `docker-compose.yml`. If you don't use cookies, remove the `./cookies.txt` volume line from `docker-compose.yml`.

> ⚠️ Using a logged-in account's cookies from a datacenter IP carries an account-ban risk; prefer a throwaway account.

### Run locally

```bash
pip install -r requirements.txt
python main.py
```

## Project structure

```
main.py              # Entry point: loads cogs and starts the bot
constants.py         # Bot IDs, regex patterns, yt-dlp/FFmpeg options, etc.
character_config.py  # Character persona, command descriptions, response text
cogs/                # Feature modules (music, character/chat, downloader, ...)
modules/             # Shared helpers (chat client, embeds, music engine, ...)
data/                # Assets (selfies, voice clips) and saved/temp state
```

## License & policies

When using this bot, please review the following documents:

- [Terms of Service](TERMS_OF_SERVICE.md)
- [Privacy Policy](PRIVACY_POLICY.md)
