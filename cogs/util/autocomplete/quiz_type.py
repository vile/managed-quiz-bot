import discord
from discord import app_commands

import cogs.util.database_interactions as db_interactions


async def autocomplete(*args, **kwargs) -> list[app_commands.Choice[str]]:
    quiz_types = await db_interactions.select_all_quiz_types()

    return [
        app_commands.Choice(name=quiz_name, value=quiz_name)
        for _, quiz_name in quiz_types
    ] or [
        app_commands.Choice(
            name="There are no current quiz types, this is a place holder.",
            value="None",
        )
    ]
