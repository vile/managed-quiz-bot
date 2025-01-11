from typing import Literal

import discord
from discord import Embed

from cogs.enum.embed_type import EmbedType
from cogs.util.embed_generator import create_embed, create_embed_error


async def send_embed(
    interaction: discord.Interaction,
    embed_type: Literal[EmbedType.NORMAL, EmbedType.ERROR] = EmbedType.NORMAL,
    is_ephemeral: bool = True,
    is_deferred: bool = True,
    **embed_kwargs,
) -> None:
    """Macro to send an interaction response with an embed"""
    match embed_type:
        case EmbedType.NORMAL:
            embed: Embed = await create_embed(**embed_kwargs)
        case EmbedType.ERROR:
            embed: Embed = await create_embed_error(**embed_kwargs)
        case _:
            embed: Embed = Embed()

    if is_deferred:
        await interaction.followup.send(embed=embed, ephemeral=is_ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=is_ephemeral)
