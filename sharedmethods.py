# General imports
import discord
import pandas as pd
import random

# Data imports
import globaldata as gld
from lilothdb import run_query as rqy


embed_colour_dict = {
    "red": discord.Colour(0xFF0000), "blue": discord.Colour(0x0000FF), "green": discord.Colour(0x00FF00),
    "purple": discord.Colour(0x800080), "orange": discord.Colour(0xFFA500), "gold": discord.Colour(0xFFD700),
    "magenta": discord.Colour(0xFF00FF), "teal": discord.Colour(0x008080), "yellow": discord.Colour(0xFFFF00),
    "cyan": discord.Colour(0x00FFFF), "pink": discord.Colour(0xFFC0CB), "brown": discord.Colour(0xA52A2A),
    "lime": discord.Colour(0x00FF00), "navy": discord.Colour(0x000080), "maroon": discord.Colour(0x800000),
    "sky_blue": discord.Colour(0x87CEEB), "indigo": discord.Colour(0x4B0082), "violet": discord.Colour(0xEE82EE),
    "turquoise": discord.Colour(0x40E0D0), "gray": discord.Colour(0x808080),
    "silver": discord.Colour(0xC0C0C0), "black": discord.Colour(0x000000), "white": discord.Colour(0xFFFFFF),
    1: 0x43B581, 2: 0x3498DB, 3: 0x9B59B6, 4: 0xF1C40F, 5: 0xCC0000,
    6: 0xE91E63, 7: 0xFFFFFF, 8: 0x000000, 9: 0x000000}


def easy_embed(colour, title, description):
    colour = colour.lower() if isinstance(colour, str) else colour
    colour = embed_colour_dict[colour] if colour in embed_colour_dict else discord.Colour.red()
    return discord.Embed(colour=colour, title=title, description=description)
