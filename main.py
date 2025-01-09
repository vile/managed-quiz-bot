import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.util.database_interactions import create_tables_if_not_exist

class QuizBot(commands.Bot):
    def __init__(self) -> None:
        client_intents = discord.Intents.default()

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=client_intents,
            help_command=None,
        )

    async def load_extensions(self) -> None:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

    async def setup_hook(self) -> None:
        await self.load_extensions()

async def main() -> None:
    load_dotenv()

    client: QuizBot = QuizBot()
    async with client:
        await client.start(os.getenv("DISCORD_BOT_TOKEN"))

if __name__ == "__main__":
    discord.utils.setup_logging()
    create_tables_if_not_exist()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("main").info("Gracefully handling keyboard interrupt")