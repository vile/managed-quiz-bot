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
class SettingsCommandsCog(commands.GroupCog, name="settings"):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.logger = logging.getLogger(f"cogs.{self.__cog_name__}")

    # Command sub groups
    manager_group: app_commands.Group = app_commands.Group(
        name="manager",
        description="Edit settings related to quiz bot managers.",
    )

    quiz_group: app_commands.Group = app_commands.Group(
        name="quiz",
        description="Edit settings related to quiz, such as the number of required correct questions.",
    )

    quiz_edit_group: app_commands.Group = app_commands.Group(
        name="quiz-edit",
        description="Edit settings for individual quizzes.",
    )

    @manager_group.command(name="add", description="Add a new bot manager.")
    async def add_bot_manager(
        self, interaction: discord.Interaction, new_manager: discord.Member
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_manager_exists(new_manager.id):
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
                await db_interactions.add_new_manager(
                    new_manager.id, interaction.user.id
                )
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
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.remove_current_manager(current_manager.id):
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

    @manager_group.command(
        name="check", description="Check if a user is an existing bot manager."
    )
    async def check_bot_manager(
        self, interaction: discord.Interaction, user_to_check: discord.Member
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            is_manager: bool = await db_interactions.check_if_manager_exists(
                user_to_check.id
            )
            self.logger.info(
                f"Successfully checked if {user_to_check.id} is a manager: {is_manager}"
            )

            if is_manager:
                await send_embed(
                    interaction, message=f"{user_to_check.mention} is a manager!"
                )
            else:
                await send_embed(
                    interaction,
                    color=discord.Colour.orange(),
                    message=f"{user_to_check.mention} is not a manager.",
                )
        except Exception as error:
            self.logger.error(
                "Some other exception occured when attempting to check manager status."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @manager_group.command(name="list", description="List all current bot managers.")
    async def list_bot_managers(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            managers: list[tuple] = await db_interactions.select_all_managers()
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

    @quiz_group.command(name="add", description="Add a new quiz type.")
    async def add_quiz_type(
        self,
        interaction: discord.Interaction,
        quiz_type: str,
        quiz_length: int,
        quiz_min_correct: int,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                self.logger.error(
                    "Quiz type already exists, aborting and notifying user."
                )

                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type already exists.",
                )
            else:
                self.logger.info(
                    "Quiz type does not exist, attempting to add new quiz type."
                )
                quiz_id: int = await db_interactions.add_quiz_type(quiz_type)
                await db_interactions.add_quiz_settings(
                    quiz_id, quiz_length, quiz_min_correct
                )

                await send_embed(
                    interaction,
                    message=f"Successfully added `{quiz_type}` as a new quiz type!",
                )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to add a new quiz type."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_group.command(name="remove", description="Remove an existing quiz type.")
    async def remove_quiz_type(
        self, interaction: discord.Interaction, quiz_type: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                if await db_interactions.remove_quiz_settings(
                    await db_interactions.select_quiz_str_to_quiz_id(quiz_type)
                ):
                    await db_interactions.remove_quiz_type(quiz_type)
                    self.logger.info(
                        f"Successfully removed quiz type {quiz_type} and associated settings."
                    )

                    await send_embed(
                        interaction,
                        message=f"Successfully removed `{quiz_type}` quiz type.",
                    )
            else:
                self.logger.error(
                    f"Did not remove quiz type {quiz_type} as it was not an existing type."
                )

                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"Did not remove quiz type {quiz_type} as it was not an existing type.",
                )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to remove a quiz type."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_group.command(name="list", description="List all existing quiz types.")
    async def list_quiz_types(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            quiz_types: tuple[str] = await db_interactions.select_all_quiz_types()
            self.logger.info("Successfully got all quiz types.")

            embed_message: str = ""
            if len(quiz_types) == 0:
                embed_message += "There are no current quiz types."
            else:
                for type in quiz_types:
                    embed_message += f"- [{str(type[0])}] `{str(type[1])}`\n"

            await send_embed(interaction, title="Quiz Types", message=embed_message)
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to list all quiz types."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_group.command(
        name="get", description="Get the settings for an existing quiz type."
    )
    async def get_quiz_type(
        self, interaction: discord.Interaction, quiz_type: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                quiz_settings: tuple = await db_interactions.select_quiz_settings(
                    quiz_type
                )
                self.logger.info(f"Successfully got quiz settings, {quiz_settings}")
                await send_embed(
                    interaction,
                    title="Quiz Settings",
                    message=f"[{quiz_settings[0]}] `{quiz_type}`\n- **Quiz Length:** {quiz_settings[1]}\n- **Required Correct Questions:** {quiz_settings[2]}\n- **Passing Grade:** {quiz_settings[2] / quiz_settings[1]:.0%}",
                )
            else:
                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type does not exist.",
                )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to get a quiz's settings."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_edit_group.command(
        name="quiz-length", description="Edit how many questions appear on a quiz."
    )
    async def change_setting_quiz_length(
        self, interaction: discord.Interaction, quiz_type: str, quiz_length: int
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                self.logger.info(
                    f"Quiz type exists, updating quiz setting: length, {quiz_length}"
                )
                quiz_id: int = await db_interactions.select_quiz_str_to_quiz_id(
                    quiz_type
                )
                await db_interactions.edit_quiz_settings_length(quiz_length, quiz_id)
                self.logger.info("Successfully update quiz setting: length")

                await send_embed(
                    interaction,
                    message=f"Updated quiz {quiz_type}'s length setting to `{quiz_length}`",
                )
            else:
                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type does not exist.",
                )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to get a quiz's length."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_edit_group.command(
        name="minimum-score",
        description="Edit what the minimum amount of correct questions is to pass.",
    )
    async def change_setting_quiz_min_correct(
        self, interaction: discord.Interaction, quiz_type: str, quiz_min_correct: int
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                self.logger.info(
                    f"Quiz type exists, updating quiz setting: min_correct, {quiz_min_correct}"
                )
                quiz_id: int = await db_interactions.select_quiz_str_to_quiz_id(
                    quiz_type
                )
                await db_interactions.edit_quiz_settings_min_correct(
                    quiz_min_correct, quiz_id
                )
                self.logger.info("Successfully update quiz setting: min_correct")

                await send_embed(
                    interaction,
                    message=f"Updated quiz {quiz_type}'s minimum correct setting to `{quiz_min_correct}`",
                )
            else:
                await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type does not exist.",
                )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to get a quiz's minimum passing score."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )


async def setup(client: commands.Bot) -> None:
    cog: SettingsCommandsCog = SettingsCommandsCog(client)
    await client.add_cog(cog, guild=discord.Object(int(os.getenv("GUILD_ID"))))
    cog.logger.info("Cog loaded")
