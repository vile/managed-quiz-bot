import logging
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import cogs.util.database_interactions as db_interactions
from cogs.descriptions.settings import *
from cogs.enum.embed_type import EmbedType
from cogs.util.autocomplete.quiz_type import \
    autocomplete as quiz_type_autocomplete
from cogs.util.ctx_interaction_check import is_manager_or_owner
from cogs.util.database_interactions import DBQuizQuestion, DBQuizSettings
from cogs.util.macro import send_embed


@app_commands.guild_only()
@is_manager_or_owner()
class SettingsCommandsCog(commands.GroupCog, name="settings"):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.logger = logging.getLogger(f"cogs.{self.__cog_name__}")

    manager_group: app_commands.Group = app_commands.Group(
        name="manager", description=GROUP_MANAGER_DESC
    )

    quiz_group: app_commands.Group = app_commands.Group(
        name="quiz", description=GROUP_QUIZ_DESC
    )

    quiz_edit_group: app_commands.Group = app_commands.Group(
        name="quiz-edit", description=GROUP_EDIT_DESC
    )

    @manager_group.command(name="add", description=CMD_MANAGER_ADD_DESC)
    @app_commands.describe(new_manager=CMD_MANAGER_ADD_MANAGER)
    async def add_bot_manager(
        self, interaction: discord.Interaction, new_manager: discord.Member
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_manager_exists(new_manager.id):
                self.logger.error(
                    "Manager already exists, aborting and notifying user."
                )
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This user is already a bot manager.",
                )

            self.logger.info(
                f"Manager does not already exist, attempting to insert new manager {new_manager.name} ({new_manager.id})."
            )
            await db_interactions.add_new_manager(new_manager.id, interaction.user.id)
            await send_embed(
                interaction,
                message=f"Successfully added {new_manager.mention} as a bot manager!",
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

    @manager_group.command(name="remove", description=CMD_MANAGER_REMOVE_DESC)
    @app_commands.describe(current_manager=CMD_MANAGER_REMOVE_MANAGER)
    async def remove_bot_manager(
        self, interaction: discord.Interaction, current_manager: discord.Member
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.remove_current_manager(current_manager.id):
                self.logger.info(
                    f"Successfully removed {current_manager.name} ({current_manager.id}) as a bot manager."
                )
                return await send_embed(
                    interaction,
                    message=f"Successfully removed {current_manager.mention} as a bot manager!",
                )

            self.logger.error(
                f"Did not remove user as a bot manager as they were not one, {current_manager.name} ({current_manager.id})."
            )
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message=f"Unsuccessfully removed {current_manager.mention} because they are not a bot manager.",
            )
        except Exception as error:
            self.logger.error(
                f"Some other exception occured when attempting to remove {current_manager.name} ({current_manager.id}) as a bot manager."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @manager_group.command(name="check", description=CMD_MANAGER_CHECK_DESC)
    @app_commands.describe(user_to_check=CMD_MANAGER_CHECK_USER)
    async def check_bot_manager(
        self, interaction: discord.Interaction, user_to_check: discord.Member
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_manager_exists(user_to_check.id):
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

    @manager_group.command(name="list", description=CMD_MANAGER_LIST_DESC)
    async def list_bot_managers(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            managers: list[tuple[int, int, int, int]] = (
                await db_interactions.select_all_managers()
            )
            self.logger.info("Successfully got all current bot managers.")

            embed_message: str = "**Current bot managers:**\n"
            if len(managers) == 0:
                embed_message += "There are no current bot managers."
            else:
                for manager in managers:
                    manager_id, discord_id, added_timestamp, added_by = manager
                    embed_message += f"- [{manager_id}] <@{discord_id}>\n (added at <t:{added_timestamp}:f> by <@{added_by}>)\n"

            await send_embed(interaction, message=embed_message)
        except Exception as error:
            self.logger.error(
                "Some other exception occured when attempting to list current bot managers."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_group.command(name="add", description=CMD_QUIZ_ADD_DESC)
    @app_commands.describe(quiz_type=CMD_QUIZ_ADD_QUIZ_TYPE)
    @app_commands.describe(quiz_length=CMD_QUIZ_ADD_QUIZ_LENGTH)
    @app_commands.describe(quiz_min_correct=CMD_QUIZ_ADD_MIN_CORRECT)
    @app_commands.describe(required_role=CMD_QUIZ_ADD_REQUIRED_ROLE)
    @app_commands.describe(passing_role=CMD_QUIZ_ADD_PASSING_ROLE_ONE)
    @app_commands.describe(passing_role_two=CMD_QUIZ_ADD_PASSING_ROLE_TWO)
    @app_commands.describe(non_passing_role=CMD_QUIZ_ADD_NON_PASSING_ROLE)
    @app_commands.describe(quiz_passed_text=CMD_QUIZ_ADD_PASSED_TEXT)
    @app_commands.describe(quiz_not_passed_text=CMD_QUIZ_ADD_NOT_PASSED_TEXT)
    async def add_quiz_type(
        self,
        interaction: discord.Interaction,
        quiz_type: str,
        quiz_length: int,
        quiz_min_correct: int,
        required_role: discord.Role,
        passing_role: discord.Role,
        passing_role_two: Optional[discord.Role],
        non_passing_role: discord.Role,
        quiz_passed_text: Optional[str],
        quiz_not_passed_text: Optional[str],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                self.logger.error(
                    "Quiz type already exists, aborting and notifying user."
                )

                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type already exists.",
                )

            self.logger.info(
                "Quiz type does not exist, attempting to add new quiz type."
            )
            quiz_id: int = await db_interactions.add_quiz_type(quiz_type)
            await db_interactions.add_quiz_settings(
                quiz_id,
                quiz_length,
                quiz_min_correct,
                required_role.id,
                passing_role.id,
                passing_role_two.id if passing_role_two is not None else None,
                non_passing_role.id,
                quiz_passed_text,
                quiz_not_passed_text,
            )

            await send_embed(
                interaction,
                message=f"Successfully added `{quiz_type}` as a new quiz type for {required_role.mention}!",
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

    @quiz_group.command(name="remove", description=CMD_QUIZ_REMOVE_DESC)
    @app_commands.describe(quiz_type=CMD_QUIZ_REMOVE_QUIZ_TYPE)
    async def remove_quiz_type(
        self, interaction: discord.Interaction, quiz_type: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if await db_interactions.check_if_quiz_type_exists(quiz_type):
                quiz_id: str = await db_interactions.select_quiz_slug_to_quiz_id(
                    quiz_type
                )

                quiz_questions: list[DBQuizQuestion] = (
                    await db_interactions.list_quiz_questions(quiz_id)
                )
                for question in quiz_questions:
                    question_id, *_ = question
                    await db_interactions.remove_quiz_question_choice(question_id)
                    await db_interactions.remove_quiz_question(question_id)

                await db_interactions.remove_quiz_settings(quiz_id)
                await db_interactions.remove_quiz_type(quiz_type)

                self.logger.info(
                    f"Successfully removed quiz type {quiz_type} and associated settings."
                )

                return await send_embed(
                    interaction,
                    message=f"Successfully removed `{quiz_type}` quiz type.",
                )

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
            self.logger.exception(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @quiz_group.command(name="list", description=CMD_QUIZ_LIST_DESC)
    async def list_quiz_types(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            quiz_types: list[tuple[int, str]] = (
                await db_interactions.select_all_quiz_types()
            )
            self.logger.info("Successfully got all quiz types.")

            embed_message: str = ""
            if len(quiz_types) == 0:
                embed_message += "There are no current quiz types."
            else:
                for type in quiz_types:
                    quiz_id, quiz_slug = type
                    embed_message += f"- [{quiz_id}] `{quiz_slug}`\n"

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

    @quiz_group.command(name="get", description=CMD_QUIZ_GET_DESC)
    @app_commands.describe(quiz_type=CMD_QUIZ_GET_QUIZ_TYPE)
    async def get_quiz_type(
        self, interaction: discord.Interaction, quiz_type: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_if_quiz_type_exists(quiz_type):
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type does not exist.",
                )

            quiz_settings: DBQuizSettings = await db_interactions.select_quiz_settings(
                quiz_type
            )
            (
                quiz_id,
                quiz_length,
                quiz_min_correct,
                quiz_required_role,
                quiz_passing_role,
                quiz_passing_role_two,
                quiz_non_passing_role,
                quiz_passed_text,
                quiz_not_passed_text,
            ) = quiz_settings

            await send_embed(
                interaction,
                title="Quiz Settings",
                message=f"[{quiz_id}] `{quiz_type}`\n- **Quiz Length:** {quiz_length}\n- **Required Correct Questions:** {quiz_min_correct}\n- **Passing Grade:** {quiz_min_correct / quiz_length:.0%}\n- **Required Role:** <@&{quiz_required_role}>\n- **Passing Role 1:** <@&{quiz_passing_role}>\n- **Passing Role 2:** {f'<@&{quiz_passing_role_two}>' if quiz_passing_role_two is not None else 'None'}\n- **Non-Passing Role:** <@&{quiz_non_passing_role}>\n- **Quiz Passed Text:** {quiz_passed_text}\n- **Quiz Not Passed Text:** {quiz_not_passed_text}",
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
        name="quiz-length", description=CMD_QUIZ_EDIT_QUIZ_LENGTH_DESC
    )
    @app_commands.describe(quiz_type=CMD_QUIZ_EDIT_QUIZ_LENGTH_QUIZ_TYPE)
    @app_commands.describe(quiz_length=CMD_QUIZ_EDIT_QUIZ_LENGTH_QUIZ_LENGTH)
    async def change_setting_quiz_length(
        self, interaction: discord.Interaction, quiz_type: str, quiz_length: int
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_if_quiz_type_exists(quiz_type):
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type does not exist.",
                )

            self.logger.info(
                f"Quiz type exists, updating quiz setting: length, {quiz_length}"
            )
            quiz_id: int = await db_interactions.select_quiz_slug_to_quiz_id(quiz_type)
            await db_interactions.edit_quiz_settings_length(quiz_length, quiz_id)
            self.logger.info("Successfully update quiz setting: length")

            await send_embed(
                interaction,
                message=f"Updated quiz {quiz_type}'s length setting to `{quiz_length}`",
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
        name="minimum-score", description=CMD_QUIZ_EDIT_MIN_SCORE_DESC
    )
    @app_commands.describe(quiz_type=CMD_QUIZ_EDIT_MIN_SCORE_QUIZ_TYPE)
    @app_commands.describe(quiz_min_correct=CMD_QUIZ_EDIT_MIN_SCORE_MIN_CORRECT)
    async def change_setting_quiz_min_correct(
        self, interaction: discord.Interaction, quiz_type: str, quiz_min_correct: int
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_if_quiz_type_exists(quiz_type):
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="This quiz type does not exist.",
                )

            self.logger.info(
                f"Quiz type exists, updating quiz setting: min_correct, {quiz_min_correct}"
            )
            quiz_id: int = await db_interactions.select_quiz_slug_to_quiz_id(quiz_type)
            await db_interactions.edit_quiz_settings_min_correct(
                quiz_min_correct, quiz_id
            )
            self.logger.info(
                f"Successfully update quiz setting: min_correct, {quiz_min_correct}"
            )

            await send_embed(
                interaction,
                message=f"Updated quiz {quiz_type}'s minimum correct setting to `{quiz_min_correct}`",
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

    @remove_quiz_type.autocomplete("quiz_type")
    @change_setting_quiz_length.autocomplete("quiz_type")
    @change_setting_quiz_min_correct.autocomplete("quiz_type")
    async def wrapper(self, *args, **kwargs) -> list[app_commands.Choice[str]]:
        result: list[app_commands.Choice[str]] = await quiz_type_autocomplete(
            self, *args, **kwargs
        )
        return result


async def setup(client: commands.Bot) -> None:
    cog: SettingsCommandsCog = SettingsCommandsCog(client)
    await client.add_cog(cog, guild=discord.Object(int(os.getenv("GUILD_ID"))))
    cog.logger.info("Cog loaded")
