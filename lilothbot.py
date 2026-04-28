# General imports
import discord
import pandas as pd
import random
import globaldata as gld

# Database imports
from lilothdb import close_database_session

guild_id = 1490035173738156034


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

    @pandora_bot.event
    async def on_ready():
        if liloth_bot.conn_status == "Connected":
            await send_log_msg(f'{liloth_bot.user} Online!')

    @pandora_bot.event
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

    @liloth_bot.hybrid_command(name='sell', help=".")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def test(ctx, cost: int):
        await ctx.defer()

