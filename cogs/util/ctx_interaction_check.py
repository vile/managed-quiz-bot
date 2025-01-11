from discord.ext.commands._types import Check, BotT
from discord.ext.commands.errors import CheckFailure
from discord.ext.commands import check, Context

from typing import Any

from cogs.util.database_interactions import check_if_manager_exists


class NotOwnerOrManager(CheckFailure):
    """Exception raised when the message author is not the owner of the bot or a manager."""

    pass


async def user_is_manager(ctx: Context) -> bool:
    """Check if the interaction's user is a manager for the bot."""
    return check_if_manager_exists(ctx.author.id)


def is_manager_or_owner() -> Check[Any]:
    """Check if the interaction's user is the bot owner or a manager for the bot."""

    async def predicate(ctx: Context[BotT]) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True

        if await user_is_manager():
            return True

        raise NotOwnerOrManager("You do not own this bot or are a bot manager.")

    return check(predicate)
