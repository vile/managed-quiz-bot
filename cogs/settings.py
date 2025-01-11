import logging
import os
import discord
from discord import app_commands
from discord.ext import commands

from cogs.util.ctx_interaction_check import is_manager_or_owner
import cogs.util.database_interactions as db_interactions

from cogs.enum.embed_type import EmbedType
from cogs.util.macro import send_embed


@app_commands.guild_only()
@is_manager_or_owner()
class SettingsCommandsCog(commands.GroupCog, name="settings"):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.logger = logging.getLogger(f"cogs.{self.__cog_name__}")

    # Command sub groups
    manager_group: app_commands.Group = app_commands.Group(
        name="manager",
        description="Edit settings related to quiz bot managers.",
    )

    # question_group: app_commands.Group = app_commands.Group(
    #     name="question",
    #     description="Edit settings related to quiz questions. This is where you edit individual quiz questions.",
    # )

    # quiz_group: app_commands.Group = app_commands.Group(
    #     name="quiz",
    #     description="Edit settings related to quiz, such as the number of required correct questions.",
    # )

    @manager_group.command(name="add", description="Add a new bot manager.")
    async def add_bot_manager(
        self, interaction: discord.Interaction, new_manager: discord.Member
    ) -> None:
        try:
            if db_interactions.check_if_manager_exists(new_manager.id):
                self.logger.error(
                    "Manager already exists, aborting and notifying user."
                )
                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This user is already a bot manager.",
                )
            else:
                self.logger.info(
                    f"Manager does not already exist, attempting to insert new manager {new_manager.name} ({new_manager.id})."
                )
                db_interactions.add_new_manager(new_manager.id, interaction.user.id)
                await send_embed(
                    interaction,
                    message=f"Successfully added {new_manager.mention} as a bot manager!",
                )
        except Exception:
            self.logger.error(
                "Some other exception happened when trying to add a new manager."
            )
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @manager_group.command(name="remove", description="Remove an existing bot manager.")
    async def remove_bot_manager(
        self, interaction: discord.Interaction, current_manager: discord.Member
    ) -> None:
        try:
            if db_interactions.remove_current_manager(current_manager.id):
                self.logger.info(
                    f"Successfully removed {current_manager.name} ({current_manager.id}) as a bot manager."
                )
                await send_embed(
                    interaction,
                    message=f"Successfully removed {current_manager.mention} as a bot manager!",
                )
            else:
                self.logger.error(
                    f"Did not remove user as a bot manager as they were not one, {current_manager.name} ({current_manager.id})."
                )
                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"Unsuccessfully removed {current_manager.mention} because they are not a bot manager.",
                )
        except Exception:
            self.logger.error(
                f"Some other exception occured when attempting to remove {current_manager.name} ({current_manager.id}) as a bot manager."
            )
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    # @manager_group.command(name="check", description="Check if a user is an existing bot manager.")
    # async def check_bot_manager() -> None: ...

    @manager_group.command(name="list", description="List all current bot managers.")
    async def list_bot_managers(self, interaction: discord.Interaction) -> None:
        try:
            managers: list[tuple] = db_interactions.select_all_managers()
            self.logger.info("Successfully got all current bot managers.")

            embed_message: str = "**Current bot managers:**\n"
            if len(managers) == 0:
                embed_message += "There are no current bot managers."
            else:
                for manager in managers:
                    embed_message += f"- [{str(manager[0])}] <@{str(manager[1])}>\n (added at <t:{str(manager[2])}:f> by <@{str(manager[3])}>)"

            await send_embed(interaction, message=embed_message)
        except Exception:
            self.logger.error(
                "Some other exception occured when attempting to list current bot managers."
            )
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    # @question_group.command(name="add", description="")
    # async def add_quiz_question() -> None: ...

    # @question_group.command(name="remove", description="")
    # async def remove_quiz_question() -> None: ...

    # @question_group.command(name="list", description="")
    # async def list_quiz_question() -> None: ...

    # @question_group.command(name="edit", description="")
    # async def () -> None: ...

    # edit how many questions are in a quiz
    # edit what number of questions need to be correct to pass

    # list role steps


async def setup(client: commands.Bot) -> None:
    cog: SettingsCommandsCog = SettingsCommandsCog(client)
    await client.add_cog(cog, guild=discord.Object(int(os.getenv("GUILD_ID"))))
    cog.logger.info("Cog loaded")
