# General imports
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot
from discord.ui import Button, View
from discord import app_commands
import asyncio
import sys
import pandas as pd
import random
from datetime import datetime as dt, timedelta, timezone as tz
from zoneinfo import ZoneInfo

# Bot imports
import globaldata as gld
import sharedmethods as sm
import menus

# Database imports
from lilothdb import run_query as rqy
from lilothdb import close_database_session

guild_id = 1490035173738156034
utc = ZoneInfo("UTC")
time_zone = ZoneInfo('America/Toronto')

# Get Bot Token
token_info = None
with open("bot_token.txt", 'r') as token_file:
    for line in token_file:
        token_info = line
TOKEN = token_info


class LilothBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.conn_status = "Connected"
        self.down_time = None
        self.cogs_loaded = False


def run_discord_bot():
    print(sys.version)
    liloth_bot = LilothBot()
    liloth_bot.invites = {}

    @liloth_bot.event
    async def on_ready():
        if liloth_bot.conn_status == "Connected":
            await send_log_msg(f'{liloth_bot.user} Online!')

    @liloth_bot.event
    async def on_resumed():
        if liloth_bot.conn_status != "Connected":
            time_msg = dt.now(utc) - liloth_bot.down_time if liloth_bot.down_time is not None else "Unknown"
            user_ping, conn_msg = '<@185530717638230016> ', f'{liloth_bot.user} Reconnected! Downtime: {time_msg}'
            conn_msg = conn_msg if liloth_bot.conn_status != 'Disconnect [Major]' else f'{user_ping}{conn_msg}'
            await send_log_msg(conn_msg if '[Major]' not in liloth_bot.conn_status else f'{user_ping}{conn_msg}')
            liloth_bot.conn_status, liloth_bot.down_time = "Connected", None

    async def send_log_msg(msg):
        log_channel = liloth_bot.get_channel(gld.bot_logging_channel)
        try:
            await log_channel.send(msg)
        except Exception as e:
            print(f"Error sending log message: {e}")

    @liloth_bot.event
    async def on_shutdown():
        await send_log_msg("Gardener Bot Off")
        try:
            await close_database_session()
            await pandora_bot.close()
        except Exception as e:
            await send_log_msg(f"Shutdown Error: {e}")

    @liloth_bot.event
    async def on_disconnect():
        liloth_bot.down_time = dt.now(utc)
        # return if already in offline status
        if liloth_bot.conn_status != 'Connected':
            return
        conn_status = "Disconnect"
        print(conn_status)
        await asyncio.sleep(10)
        if not liloth_bot.is_closed():
            conn_status = "Disconnect [Standard]"
            await send_log_msg("Gardener Bot Disconnect [Standard]")
        await asyncio.sleep(50)
        if liloth_bot.is_closed():
            conn_status = "Disconnect [Major]"
            await send_log_msg("<@185530717638230016>\nGardener Bot Disconnect [Escalated]!")

    @liloth_bot.hybrid_command(name='sync', help="Sync the slash commands")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def sync(ctx):
        await ctx.defer()
        if user.id not in [gld.admins["Archael"]]:
            await ctx.send("DO NOT TOUCH")
            return
        synced = await liloth_bot.tree.sync(guild=discord.Object(id=guild_id))
        print(f"Liloth Bot Synced! {len(synced)} command(s)")
        await ctx.send('Liloth Bot commands synced!')

    @liloth_bot.hybrid_command(name='test', help=".")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def test(ctx):
        await ctx.defer()
        if user.id not in [gld.admins["Archael"]]:
            await ctx.send("DO NOT TOUCH")
            return
        await ctx.send("TESTING")

    @liloth_bot.hybrid_command(name='redeem', help="Access the coin/point shops.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def redeem(ctx):
        if ctx.channel.id not in [1498478242875576491, 1498478333623537855]:
            await ctx.send("Please use <#1498478242875576491>")
            return
        menu_embed = sm.easy_embed("Purple", "Shop Select", "Select a shop type to continue:")
        shop_select = menus.ShopSelect(ctx.author)
        await ctx.send(embed=menu_embed, view=shop_select)

    @liloth_bot.hybrid_command(name='inventory', help="Check your inventory.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def inventory(ctx):
        await ctx.defer()
        if ctx.channel.id not in [1498478242875576491, 1498478333623537855]:
            await ctx.send("Please use <#1498478242875576491>")
            return
        inventory_query = f"SELECT * FROM UserCoins WHERE discord_id = :user_id"
        params = {"user_id": str(ctx.author.id)}
        coin_data = await rqy(inventory_query, params=params, return_value=True)
        if coin_data is None or coin_data.empty:
            await ctx.send("Inventory is empty")
            return
        description = (f"{gld.flower_icon} {int(coin_data['flower_points'].values[0]):,}x Flowers\n"
                       f"{gld.gold_icon} {int(coin_data['gold_coins'].values[0]):,}x Gold Coins\n"
                       f"{gld.diamond_icon} {int(coin_data['diamond_coins'].values[0]):,}x Diamond Coins")
        embed = sm.easy_embed("Purple", f"{ctx.author.display_name}'s Inventory", description)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @liloth_bot.hybrid_command(name='give_coins', help="Gives coins to a user [Liloth Only].")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def give_coins(ctx, user: discord.User, quantity=1):
        await ctx.defer()
        if user.id not in [gld.admins["Liloth"]]:
            await ctx.send("No cheating!")
            return
        menu_embed = sm.easy_embed("Purple", "Coin Select", "[Liloth Only] Select coin type to assign.")
        coin_select = menus.CoinSelect(user, quantity)
        await ctx.send(embed=menu_embed, view=coin_select)

    @liloth_bot.hybrid_command(name='reset_coins', help="Reset a user's coin and leaderboard data.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def reset_coins(ctx, user: discord.User):
        await ctx.defer()
        if ctx.author.id not in [gld.admins["Liloth"]]:
            await ctx.send("Invalid access!")
            return
        reset_query = ("UPDATE UserCoins SET leaderboard_points = 0, flower_points = 0, flower_points_total = 0, "
                       "vip_coins = 0, vip_coins_total = 0, silver_coins = 0, silver_coins_total = 0, gold_coins = 0, "
                       "gold_coins_total = 0, diamond_coins = 0, diamond_coins_total = 0 WHERE discord_id = :user_id")
        params = {"user_id": str(user.id)}
        await rqy(reset_query, params=params)
        embed = sm.easy_embed("Red", "Reset", f"{user.display_name}'s data has been reset.")
        await ctx.send(embed=embed)

    @liloth_bot.hybrid_command(name='remove_coins', help="Removes coins from a user [Liloth Only].")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def remove_coins(ctx, user: discord.User, quantity=1):
        await ctx.defer()
        if user.id not in [gld.admins["Liloth"]]:
            await ctx.send("No cheating!")
            return
        menu_embed = sm.easy_embed("Purple", "Coin Select", "[Liloth Only] Select coin type to deduct.")
        coin_select = menus.CoinSelect(user, quantity, increase=False)
        await ctx.send(embed=menu_embed, view=coin_select)

    @liloth_bot.hybrid_command(name='leaderboard', help="View the garden leaderboard.")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def leaderboard(ctx):
        await ctx.defer()
        leaderboard_select = menus.LeaderboardView()
        embed = await menus.build_leaderboard_embed(ctx.guild, "Score")
        await ctx.send(embed=embed, view=leaderboard_select)
        await ranking_check(ctx.guild)

    async def ranking_check(guild):
        ranking_role_name = "Sapphire Heart - Leaderboard Rank"
        ranking_columns = ["leaderboard_points", "vip_coins_total", "silver_coins_total",
                           "gold_coins_total", "diamond_coins_total"]
        ranking_role = discord.utils.get(guild.roles, name=ranking_role_name)
        if ranking_role is None:
            return
        rank_1_user_ids = []
        for column_name in ranking_columns:
            query = (f"SELECT discord_id, {column_name} FROM UserCoins WHERE {column_name} > 0 "
                     f"ORDER BY {column_name} DESC LIMIT 1")
            rank_data = await rqy(query, return_value=True)
            if rank_data is not None and not rank_data.empty:
                rank_1_user_ids.append(int(rank_data["discord_id"].values[0]))
        for member in ranking_role.members:
            if member.id not in rank_1_user_ids:
                await member.remove_roles(ranking_role)
        for user_id in rank_1_user_ids:
            member = guild.get_member(user_id)
            if member is not None and ranking_role not in member.roles:
                await member.add_roles(ranking_role)

    # Run the bot ------------------------------------------
    liloth_bot.run(TOKEN)

