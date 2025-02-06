import logging
import os
from typing import Final, Optional

import discord
from discord import app_commands
from discord.ext import commands

import cogs.util.database_interactions as db_interactions
from cogs.descriptions.questions import *
from cogs.enum.embed_type import EmbedType
from cogs.util.autocomplete.quiz_type import \
    autocomplete as quiz_type_autocomplete
from cogs.util.ctx_interaction_check import is_manager_or_owner
from cogs.util.macro import send_embed

MAX_EMBED_DESCRIPTION_LENGTH: Final[int] = 4_000
QUESTIONS_PER_AGE: Final[int] = 5
TEN_MINUTES: Final[float] = float(10 * 60)
PreparedAnswers = list[bool]


class PaginatorView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed]):
        super().__init__(timeout=TEN_MINUTES)
        self.embeds = embeds
        self.current_page = 0

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.grey, disabled=True)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page -= 1
        await self.update_buttons(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.grey)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_page += 1
        await self.update_buttons(interaction)

    async def update_buttons(self, interaction: discord.Interaction):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
        await interaction.response.edit_message(
            embed=self.embeds[self.current_page], view=self
        )


class PreparedAnswersTransformer(app_commands.Transformer):
    """Argument converter that takes a unsorted string of numbers and converts to a sorted list of bools.

    \"31\" -> [True, False, True, False, False], where the first (0th) and third (2nd) items are `True`.
    """

    def __init__(self) -> None:
        self.target_numbers = ["1", "2", "3", "4", "5"]
        super().__init__()

    async def transform(self, _: discord.Interaction, argument: str) -> PreparedAnswers:
        return [num in "".join(sorted(argument)) for num in self.target_numbers]


@app_commands.guild_only()
@is_manager_or_owner()
class QuestionsCommandsCog(commands.GroupCog, name="questions"):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.logger = logging.getLogger(f"cogs.{self.__cog_name__}")

    @app_commands.command(name="add", description=CMD_ADD_DESC)
    @app_commands.describe(quiz_type=CMD_ADD_QUIZ_TYPE)
    @app_commands.describe(image=CMD_ADD_IMAGE)
    @app_commands.describe(question_text=CMD_ADD_QUESTION_TEXT)
    @app_commands.describe(correct_answers=CMD_ADD_CORRECT_ANSWERS)
    @app_commands.describe(correct_answer_text=CMD_ADD_CORRECT_ANSWER_TEXT)
    @app_commands.describe(incorrect_answer_text=CMD_ADD_INCORRECT_ANSWER_TEXT)
    @app_commands.describe(answer_one=CMD_ADD_ANSWER_ONE)
    @app_commands.describe(answer_two=CMD_ADD_ANSWER_TWO)
    @app_commands.describe(answer_three=CMD_ADD_ANSWER_THREE)
    @app_commands.describe(answer_four=CMD_ADD_ANSWER_FOUR)
    @app_commands.describe(answer_five=CMD_ADD_ANSWER_FIVE)
    async def add_question(
        self,
        interaction: discord.Interaction,
        quiz_type: str,
        image: Optional[str],
        question_text: str,
        correct_answers: app_commands.Transform[
            PreparedAnswers, PreparedAnswersTransformer
        ],
        correct_answer_text: str,
        incorrect_answer_text: str,
        answer_one: str,
        answer_two: str,
        answer_three: Optional[str],
        answer_four: Optional[str],
        answer_five: Optional[str],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            answer_list: list[Optional[str]] = [
                answer_one,
                answer_two,
                answer_three,
                answer_four,
                answer_five,
            ]

            # There must be at least one correct answer
            if correct_answers.count(True) == 0:
                self.logger.error(
                    "Supplied question data does not contain at least one correct choice."
                )
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="At least one choice must be the correct choice.",
                )

            # The correct answer(s) must belong to a choice that is not `None`
            if not all(
                [
                    (
                        correct_answers[i]
                        and answer_list[i] is not None
                        or not correct_answers[i]
                    )
                    for i in range(5)
                ]
            ):
                self.logger.error(
                    "Supplied question data does not contain a correct choice for any non-None choices."
                )
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="Ensure that the correct answer(s) supplied are filled choices.",
                )

            if not await db_interactions.check_if_quiz_type_exists(quiz_type):
                self.logger.info("Supplied quiz type does not exist")
                return await send_embed(
                    interaction,
                    message="The quiz type you supplied doesn't exist. Make sure inputting the exact quiz type and that it exists.",
                )

            quiz_id: int = await db_interactions.select_quiz_slug_to_quiz_id(quiz_type)
            question_id = await db_interactions.add_quiz_question(
                question_text,
                correct_answer_text,
                incorrect_answer_text,
                image,
                quiz_id,
                interaction.user.id,
            )
            for idx, answer in enumerate(answer_list):
                if answer is not None:
                    await db_interactions.add_quiz_question_choice(
                        question_id, answer, correct_answers[idx]
                    )

            self.logger.info("Successfully added new question with answers")
            await send_embed(
                interaction, message="Successfully added new quiz question!"
            )

        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to add a quiz question."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @app_commands.command(name="remove", description=CMD_REMOVE_DESC)
    @app_commands.describe(question_id=CMD_REMOVE_QUESTION_ID)
    async def remove_question(
        self, interaction: discord.Interaction, question_id: int
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_quiz_question_exists(question_id):
                self.logger.error("Supplied question id does not exist.")
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"Question id `{question_id}` does not exist.",
                )

            if not await db_interactions.remove_quiz_question_choice(question_id):
                self.logger.error("Failed to remove question choices.")
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="There seems to have been an error removing the questions choices.",
                )

            if not await db_interactions.remove_quiz_question(question_id):
                self.logger.error("Failed to remove question.")
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="There seems to have been an error removing the question.",
                )

            await send_embed(
                interaction,
                message=f"Successfully removed question id `{question_id}`!",
            )

        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to remove question and associated choices."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @app_commands.command(name="list", description=CMD_LIST_DESC)
    @app_commands.describe(quiz_type=CMD_LIST_QUIZ_TYPE)
    async def list_questions(
        self, interaction: discord.Interaction, quiz_type: str
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_if_quiz_type_exists(quiz_type):
                self.logger.error(
                    "Can't list questions for a quiz type that does not exist."
                )
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"`{quiz_type}` is not a valid quiz type.",
                )

            # question id, question text, question image, quiz id, created by, created at
            quiz_id = await db_interactions.select_quiz_slug_to_quiz_id(quiz_type)
            questions = await db_interactions.list_quiz_questions(quiz_id)

            if len(questions) == 0:
                return await send_embed(
                    interaction, message="There are no questions for this quiz."
                )

            embeds: list[discord.Embed] = []
            description_text: str = ""
            page_count: int = 0

            for idx, question in enumerate(questions):
                (
                    question_id,
                    question_text,
                    correct_answer_text,
                    incorrect_answer_text,
                    question_image,
                    _,
                    created_by,
                    created_at,
                ) = question
                answer_choices = await db_interactions.list_quiz_question_choices(
                    question_id
                )
                answer_text: str = ""
                for idx, choice in enumerate(answer_choices):
                    _, _, choice_text, is_correct = choice
                    answer_text += f"- {'**' if is_correct else ''}{chr(ord('@') + (idx + 1))}: {choice_text}{'**' if is_correct else ''}\n"

                section_text: str = (
                    f"`[{question_id}]` **{question_text}**\n- Created By: <@{created_by}>\n- Created At: <t:{created_at}:f>\n- Image Link: {'None' if question_image is None else f'[image]({question_image})'}\n- Correct Answer Text: {correct_answer_text}\n- Incorrect Answer Text: {incorrect_answer_text}\n**Answer Choices:**\n{answer_text}\n"
                )

                if (
                    len(description_text) + len(section_text)
                    >= MAX_EMBED_DESCRIPTION_LENGTH
                    or (idx + 1) % QUESTIONS_PER_AGE == 0
                ):
                    embed: discord.Embed = discord.Embed(
                        color=discord.Colour.green(),
                        description=description_text,
                        title=f"Quiz Questions (Page {page_count + 1})",
                    )
                    embeds.append(embed)
                    description_text = section_text
                    page_count += 1
                else:
                    description_text += section_text

            else:
                if len(description_text) > 0:
                    embed: discord.Embed = discord.Embed(
                        color=discord.Colour.green(), description=description_text
                    )
                    embeds.append(embed)

            await interaction.followup.send(embed=embeds[0], view=PaginatorView(embeds))
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to list questions."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @add_question.autocomplete("quiz_type")
    @list_questions.autocomplete("quiz_type")
    async def wrapper(self, *args, **kwargs) -> list[app_commands.Choice[str]]:
        result: list[app_commands.Choice[str]] = await quiz_type_autocomplete(
            self, *args, **kwargs
        )
        return result


async def setup(client: commands.Bot) -> None:
    cog: QuestionsCommandsCog = QuestionsCommandsCog(client)
    await client.add_cog(cog, guild=discord.Object(int(os.getenv("GUILD_ID"))))
    cog.logger.info("Cog loaded")
