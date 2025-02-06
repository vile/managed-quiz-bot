import logging
import os
from dataclasses import dataclass
from random import sample
from typing import Final, Union

import discord
from discord import app_commands
from discord.ext import commands

import cogs.util.database_interactions as db_interactions
from cogs.descriptions.quiz import *
from cogs.enum.embed_type import EmbedType
from cogs.util.autocomplete.quiz_type import \
    autocomplete as quiz_type_autocomplete
from cogs.util.database_interactions import (DBQuizChoice, DBQuizQuestion,
                                             DBQuizSettings)
from cogs.util.macro import send_embed

VIEW_TIMEOUT: Final[float] = 600.0  # 10 minutes


@dataclass
class QuestionChoice:
    choice_text: str
    is_correct: bool


@dataclass
class QuizQuestion:
    idx: int
    question_text: str
    correct_answer_text: str
    incorrect_answer_text: str
    image: Union[str, None]
    choices: list[QuestionChoice]


class QuizView(discord.ui.View):
    def __init__(
        self,
        question_id: int,
        choices: list[QuestionChoice],
        correct_answer_text: str,
        incorrect_answer_text: str,
        user: discord.User,
    ) -> None:
        super().__init__(timeout=VIEW_TIMEOUT)
        self.question_id = question_id
        self.correct_answer_text = correct_answer_text
        self.incorrect_answer_text = incorrect_answer_text
        self.user_answers = []
        self.answered_correctly = False
        self.user = user
        self.single_answer = False

        if [choice.is_correct for choice in choices].count(True) == 1:
            self.single_answer = True

        for idx, choice in enumerate(choices):
            choice_letter: str = chr(ord("@") + (idx + 1))
            self.add_item(QuizChoiceButton(choice_letter, choice.is_correct))

        self.add_item(QuizSubmitButton())

    async def on_timeout(self) -> None:
        await self.disable_children()

    async def disable_children(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.response:
            await self.response.edit(view=self)


class QuizChoiceButton(discord.ui.Button):
    def __init__(self, label: str, is_correct: bool) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.gray)
        self.is_correct = is_correct

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if self.view.single_answer:
            self.view.user_answers = [self.label]

            for child in self.view.children:
                if child.label != "Submit":
                    child.style = discord.ButtonStyle.gray

            self.style = discord.ButtonStyle.green
        else:
            if self.label in self.view.user_answers:
                self.view.user_answers.remove(self.label)
                self.style = discord.ButtonStyle.gray
            else:
                self.view.user_answers.append(self.label)
                self.style = discord.ButtonStyle.green

        await interaction.edit_original_response(view=self.view)


class QuizSubmitButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Submit", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        if len(self.view.user_answers) == 0:
            followup_message: discord.WebhookMessage = await interaction.followup.send(
                "You must select at least one answer."
            )
            await followup_message.delete(delay=10.0)
            return

        await self.view.disable_children()

        if await self.are_answers_correct():
            embed: discord.Embed = discord.Embed(
                description=self.view.correct_answer_text,
                color=discord.Colour.green(),
            )
            await interaction.followup.send(embed=embed)
            self.view.answered_correctly = True
        else:
            embed: discord.Embed = discord.Embed(
                description=self.view.incorrect_answer_text,
                color=discord.Colour.orange(),
            )
            await interaction.followup.send(embed=embed)

        self.view.stop()

    async def are_answers_correct(self) -> bool:
        answers_checked: list[bool] = []
        for child in self.view.children:
            if child.label == self.label:
                continue

            # user selected a correct answer
            if child.label in self.view.user_answers and child.is_correct:
                answers_checked.append(True)
            # user selected a wrong answer
            elif child.label in self.view.user_answers and not child.is_correct:
                answers_checked.append(False)
            # user did not select a right answer
            elif child.label not in self.view.user_answers and child.is_correct:
                answers_checked.append(False)
            # user did not select a wrong answer
            elif child.label not in self.view.user_answers and not child.is_correct:
                answers_checked.append(True)

        correct: bool = all(answers_checked)

        await db_interactions.insert_question_stat(
            self.view.user.id, self.view.question_id, correct
        )
        return correct


class EthWalletInputView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.eth_wallet_address = None

    @discord.ui.button(label="Enter Wallet", style=discord.ButtonStyle.primary)
    async def enter_wallet(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(EthWalletInputModal(self))

    async def disable_children(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.response:
            await self.response.edit(view=self)


class EthWalletInputModal(discord.ui.Modal):
    def __init__(self, parent_view: EthWalletInputView) -> None:
        super().__init__(title="Wallet Input", timeout=VIEW_TIMEOUT)
        self.parent_view = parent_view

    eth_wallet_address = discord.ui.TextInput(
        label="ETH Address",
        placeholder="0x0000000000000000000000000000000000000000",
        min_length=42,
        max_length=42,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.parent_view.eth_wallet_address = self.eth_wallet_address.value

        await interaction.response.send_message(
            f"Thank you for your wallet address, {interaction.user.mention}!"
        )

        await self.parent_view.disable_children()
        self.parent_view.stop()


class QuizCommandsCog(commands.GroupCog, name="quiz"):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.logger = logging.getLogger(f"cogs.{self.__cog_name__}")
        self.active_quiz_users: list[int] = []

    @app_commands.command(name="start", description=CMD_QUIZ_START_DESC)
    @app_commands.describe(quiz=CMD_QUIZ_START_QUIZ)
    async def start_quiz(
        self,
        interaction: discord.Interaction,
        quiz: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if not await db_interactions.check_if_quiz_type_exists(quiz):
                self.logger.error(f"Supplied quiz type {quiz} does not exist.")
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"There doesn't seem to be a quiz for `{quiz}`. Make sure you are selecting a suggested quiz type!",
                )

            # ensure that the quiz the user is starting has the required role
            quiz_settings: DBQuizSettings = await db_interactions.select_quiz_settings(
                quiz
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

            required_role: discord.Role = discord.utils.get(
                interaction.guild.roles, id=quiz_required_role
            )
            if required_role not in interaction.user.roles:
                self.logger.error(
                    f"User does not have requried role to start quiz {required_role=}"
                )
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message=f"You do not have the required role to start this quiz, {required_role.mention}",
                )

            # make sure a user can only have 1 quiz active at a time
            if interaction.user.id in self.active_quiz_users:
                self.logger.error("User already has an active quiz.")
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="You already have an active quiz. Visit the bot's DMs to continue.",
                )

            self.active_quiz_users.append(interaction.user.id)

            # send user a dm notification of the quiz starting
            await interaction.user.send(f"Preparing your `{quiz}` quiz now!\n\n**Each question has a time limit of {VIEW_TIMEOUT / 60:.1f} minutes.**")

            # get set of questions (questions are randomized during view creation)
            question_bank: list[DBQuizQuestion] = (
                await db_interactions.list_quiz_questions(quiz_id)
            )
            parsed_questions: list[QuizQuestion] = []
            for question in question_bank:
                (
                    idx,
                    question_text,
                    correct_answer_text,
                    incorrect_answer_text,
                    image,
                    *_,
                ) = question

                choice_bank: list[DBQuizChoice] = (
                    await db_interactions.list_quiz_question_choices(idx)
                )
                parsed_choices: list[QuestionChoice] = []
                for choice in choice_bank:
                    *_, choice_text, is_correct = choice
                    parsed_choices.append(QuestionChoice(choice_text, bool(is_correct)))

                parsed_questions.append(
                    QuizQuestion(
                        idx,
                        question_text,
                        correct_answer_text,
                        incorrect_answer_text,
                        image,
                        parsed_choices,
                    )
                )

            if (final_quiz_length := len(parsed_questions)) < quiz_length:
                self.active_quiz_users.remove(interaction.user.id)
                self.logger.error(
                    f"Not enough questions in pool to fill quiz. {final_quiz_length=} {quiz_length=}"
                )
                await interaction.user.send(
                    f"There was an error starting your quiz, please see {interaction.channel.mention} for more info."
                )
                return await send_embed(
                    interaction,
                    embed_type=EmbedType.ERROR,
                    message="Sorry, it looks like there aren't enough questions for this quiz. Contact a mod to solve this issue.",
                )

            self.logger.debug(parsed_questions)
            await send_embed(
                interaction,
                message=f"Check your DMs to start your quiz! [Jump to DMs](https://discord.com/channels/@me/{interaction.user.dm_channel.id}).",
            )

            wallet_modal: EthWalletInputView = EthWalletInputView()
            wallet_modal.response = await interaction.user.send(view=wallet_modal)
            await wallet_modal.wait()

            # dm user the quiz view
            total_correct_questions: int = 0
            for idx, question in enumerate(sample(parsed_questions, quiz_length)):
                answer_text: str = ""
                num_correct_answers: int = 0
                for idy, choice in enumerate(question.choices):
                    if choice.is_correct:
                        num_correct_answers += 1

                    answer_text += (
                        f"- {chr(ord('@') + (idy + 1))}) {choice.choice_text}\n"
                    )

                embed: discord.Embed = discord.Embed(
                    title=f"Question #{idx + 1}",
                    description=f"**{question.question_text}**\n{answer_text}",
                    color=discord.Colour.blue(),
                )

                if num_correct_answers > 1:
                    embed.set_footer(text="There many be multiple correct answers.")

                if question.image:
                    embed.set_image(url=question.image)

                view: QuizView = QuizView(
                    question.idx,
                    question.choices,
                    question.correct_answer_text,
                    question.incorrect_answer_text,
                    interaction.user,
                )
                view.response = await interaction.user.send(embed=embed, view=view)
                await view.wait()

                if view.answered_correctly:
                    total_correct_questions += 1

            if total_correct_questions >= quiz_min_correct:
                embed: discord.Embed = discord.Embed(
                    title="You passed!",
                    description=f"Quiz score: {total_correct_questions} out of {len(parsed_questions)}\nMinimum score: {quiz_min_correct / quiz_length:.0%} ({quiz_min_correct} correct answers){f'\n**{quiz_passed_text}**' if quiz_passed_text is not None else ''}",
                    color=discord.Colour.green(),
                )

                roles: list[discord.Object] = [
                    discord.Object(id=quiz_passing_role),
                ]
                if quiz_passing_role_two is not None:
                    roles.append(discord.Object(id=quiz_passing_role_two))

                await interaction.user.add_roles(
                    *roles,
                    reason=f"User passed {quiz} quiz",
                )
                await db_interactions.insert_quiz_stat(
                    interaction.user.id,
                    quiz_id,
                    True,
                    wallet_modal.eth_wallet_address,
                )
            else:
                embed: discord.Embed = discord.Embed(
                    title="You're almost there!",
                    description=f"Quiz score: {total_correct_questions} out of {len(parsed_questions)}\nMinimum score: {quiz_min_correct / quiz_length:.0%} ({quiz_min_correct} correct answers){f'\n**{quiz_not_passed_text}**' if quiz_not_passed_text is not None else ''}",
                    color=discord.Colour.yellow(),
                )

                await interaction.user.add_roles(
                    discord.Object(id=quiz_non_passing_role),
                    reason=f"User did not pass {quiz} quiz",
                )
                await db_interactions.insert_quiz_stat(
                    interaction.user.id,
                    quiz_id,
                    False,
                    wallet_modal.eth_wallet_address,
                )

            await interaction.user.remove_roles(
                discord.Object(id=quiz_required_role),
                reason=f"User has attempted {quiz} quiz",
            )

            await interaction.user.send(content="Quiz complete!", embed=embed)
            self.active_quiz_users.remove(interaction.user.id)
        except discord.Forbidden:
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="Sorry, it looks like you don't have DMs enabled. Please enable your DMs to start this quiz!",
            )
        except Exception as error:
            self.logger.error(
                "Some other exception happened when trying to start a quiz."
            )
            self.logger.error(error)
            await send_embed(
                interaction,
                embed_type=EmbedType.ERROR,
                message="An error occured when trying to query the database. Try again.",
            )

    @start_quiz.autocomplete("quiz")
    async def wrapper(self, *args, **kwargs) -> list[app_commands.Choice[str]]:
        result: list[app_commands.Choice[str]] = await quiz_type_autocomplete(
            self, *args, **kwargs
        )
        return result


async def setup(client: commands.Bot) -> None:
    cog: QuizCommandsCog = QuizCommandsCog(client)
    await client.add_cog(cog, guild=discord.Object(int(os.getenv("GUILD_ID"))))
    cog.logger.info("Cog loaded")
