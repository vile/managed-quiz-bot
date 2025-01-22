import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import cogs.util.database_interactions as db_interactions
from cogs.enum.embed_type import EmbedType
from cogs.util.ctx_interaction_check import is_manager_or_owner
from cogs.util.macro import send_embed


@app_commands.guild_only()
@is_manager_or_owner()
class StatsCommandsCog(commands.GroupCog, name="stats"):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.logger = logging.getLogger(f"cogs.{self.__cog_name__}")

    get_group: app_commands.Group = app_commands.Group(
        name="get",
        description="Get aggregate or individual stats about quizzes or questions.",
    )

    @get_group.command(
        name="user-quiz",
        description="Get passing and timestamp data about a user's quiz.",
    )
    async def get_user_quiz(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            user_stats = await db_interactions.select_quiz_stats_for_user(user.id)

            message: str = ""
            for stat in user_stats:
                quiz_passed, quiz_timestamp, quiz_slug = stat
                message += f"{user.mention} {'did' if quiz_passed else 'did not'} pass `{quiz_slug}` quiz at <t:{quiz_timestamp}:f>\n"

            await send_embed(
                interaction,
                title=f"Quiz stats for {user.display_name}",
                message=message,
            )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to add a new manager."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @get_group.command(
        name="aggregate-quiz", description="Get an aggregate data overview of a quiz."
    )
    async def _(self, interaction: discord.Interaction, quiz: str) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_if_quiz_type_exists(quiz):
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"Quiz type `{quiz}` does not exist.",
                )

            quiz_id = await db_interactions.select_quiz_str_to_quiz_id(quiz)
            agg_stats = await db_interactions.select_quiz_stats_aggregate(quiz_id)
            (
                total_quiz_attempts,
                total_pass_rate,
                _,
                quiz_pass_rate,
                quiz_attempts,
                oldest_attempt,
                newest_attempt,
            ) = agg_stats

            await send_embed(
                interaction,
                title=f"Aggregate stats for {quiz} quiz",
                message=f"Global Quiz Attempts: **{total_quiz_attempts}** (including all quiz types)\nGlobal Quiz Pass Rate: **{total_pass_rate:.2%}**\n{quiz.capitalize()} Quiz Attempts: **{quiz_attempts}**\n{quiz.capitalize()} Pass Rate: **{quiz_pass_rate:.2%}**\nOldest Quiz Attempt: <t:{oldest_attempt}:f>\nLatest Quiz Attempt: <t:{newest_attempt}:f>",
            )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to add a new manager."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )


async def setup(client: commands.Bot) -> None:
    cog: StatsCommandsCog = StatsCommandsCog(client)
    await client.add_cog(cog, guild=discord.Object(int(os.getenv("GUILD_ID"))))
    cog.logger.info("Cog loaded")
