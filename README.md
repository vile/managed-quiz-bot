# Managed Quiz Bot

![Python Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fvile%2Fmanaged-quiz-bot%2Fmaster%2Fpyproject.toml&query=%24.tool.poetry.dependencies.python&label=python)
[![Discord.py Package Version](https://img.shields.io/badge/discord.py-2.4.0-green)](https://github.com/Rapptz/discord.py)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)

A Discord bot developed for [Boring Security DAO](https://x.com/BoringSecDAO) to automate the process of taking quizzes (and associated admin tasks).

## Requirements

1. Git - [Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
   1. Check if you have Git installed with `git --version`
2. Python (3.12.8) - [Install Python (Windows)](https://www.python.org/downloads/windows/), [Install Python (Linux)](https://docs.python.org/3/using/unix.html)
   1. Check if you have Python installed with `python3 --version`
3. Pip - [Install Pip](https://pip.pypa.io/en/stable/installation/)
   1. Check if you have Pip installed with `pip --version`
4. Poetry - [Install Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer) (preferrably with [pipx](https://github.com/pypa/pipx))
   1. Check if you have Poetry installed with `poetry --version`

## Usage

### Installing

#### Clone This Repo

```bash
git clone https://github.com/vile/managed-quiz-bot.git
cd managed-quiz-bot
```

#### Rename Example .env File

```bash
mv .env.example .env
```

Include your bot's token (`DISCORD_BOT_TOKEN`) and the guild ID (`GUILD_ID`) where you will use the bot in this file.

### Quick Start

```bash
make # Configure Poetry, install packages, start the bot using Poetry
```

### Normal Start

```bash
poetry config virtualenvs.in-project true # Only required once
poetry install --no-root # Install packages
poetry run python3 main.py # Start the bot
```

You can also start the bot to run in the background (such as on a VPS):

```bash
nohup poetry run python3 main.py & # Start the bot and run in the background
tail -f nohup.out # Read the live log file
```

### Sync Commands to Guild

To make application commands available in the server, mention the bot to invoke the `sync` text command.
Where `~` syncs all guild commands to the current guild (see: [command body](https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html#command-body), [archive](https://archive.ph/vsSFz)).
Make sure the bot has the `Send Messages` permission in the channel where you are mentioning the bot.

This is only available to the bot owner (or all team members if the bot belongs to a team).

```text
<@BOT_USER_ID> sync ~
```

If application commands are not synced to the guild, the bot integration will show that "this application has no commands," (rendering all commands unusable) and autocomplete will not work.
