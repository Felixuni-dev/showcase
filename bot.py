import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
import signal
import traceback

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("discord_bot")

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
app_id = os.getenv("APPLICATION_ID")

if not token or not app_id:
    log.critical("Looks like the bot token or app ID aren't set in the .env file.")
    exit(1)

prefix = "?"
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

the_bot = commands.Bot(command_prefix=prefix, intents=intents, application_id=int(app_id))
the_bot.remove_command("help")

# --- Some core bot events ---
@the_bot.event
async def on_ready():
    print(f"Bot's up and running as {the_bot.user}!")
    try:
        synced = await the_bot.tree.sync()
        print(f"Synced {len(synced)} slash commands. Cool!")
    except Exception:
        log.error("Failed to sync slash commands.", exc_info=True)

@the_bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, 'on_error'):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Whoops! Looks like you don't have the permissions for that command.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        log.error(f"Something went wrong with '{ctx.command}': {error}", exc_info=True)
        await ctx.send(f"Hmm, ran into a problem with that command. Maybe try again?")

# --- Cog loading stuff ---
async def _load_cog(bot, ext):
    try:
        await bot.load_extension(f"cogs.{ext}")
        log.info(f"Loaded cog: {ext}")
        return True
    except Exception as e:
        log.error(f"Couldn't load cog '{ext}': {e}", exc_info=True)
        return False

async def _unload_cog(bot, ext):
    try:
        await bot.unload_extension(f"cogs.{ext}")
        log.info(f"Unloaded cog: {ext}")
        return True
    except Exception as e:
        log.error(f"Couldn't unload cog '{ext}': {e}", exc_info=True)
        return False

@the_bot.command()
@commands.has_permissions(administrator=True)
async def load_cog(ctx, extension):
    """Loads a specific cog."""
    if await _load_cog(the_bot, extension):
        await ctx.send(f"Alright, '{extension}' is loaded up!")
    else:
        await ctx.send(f"Failed to load '{extension}'. Check the logs.")

@the_bot.command()
@commands.has_permissions(administrator=True)
async def unload_cog(ctx, extension):
    """Unloads a specific cog."""
    if await _unload_cog(the_bot, extension):
        await ctx.send(f"Yep, '{extension}' is unloaded.")
    else:
        await ctx.send(f"Couldn't unload '{extension}'. Hmm.")

@the_bot.command()
@commands.has_permissions(administrator=True)
async def reload_cog(ctx, extension):
    """Reloads a specific cog."""
    if await _unload_cog(the_bot, extension) and await _load_cog(the_bot, extension):
        await ctx.send(f"Refreshed '{extension}'. All good!")
    else:
        await ctx.send(f"Something went wrong reloading '{extension}'. See the logs.")

async def load_all_the_cogs():
    """Finds and loads all cogs in the ./cogs directory."""
    for root, _, files in os.walk("./cogs"):
        for filename in files:
            if filename.endswith(".py"):
                cog_path = os.path.relpath(os.path.join(root, filename), start="./cogs")
                cog_name = cog_path.replace("\\", ".").replace("/", ".")[:-3]
                await _load_cog(the_bot, cog_name)

# --- Owner-only restart command ---
@the_bot.command()
@commands.is_owner()
async def reboot(ctx):
    """Restarts the bot and reloads all cogs."""
    await ctx.send("Going down for a quick reboot...")
    log.info("Bot is restarting...")
    for cog in list(the_bot.extensions.keys()):
        await _unload_cog(the_bot, cog)
    await load_all_the_cogs()
    await ctx.send("Back online and all cogs reloaded!")
    log.info("Bot restarted and cogs reloaded.")

# --- shutdown ---
def handle_shutdown(*args):
    log.info("Received shutdown signal. Cleaning up...")
    asyncio.get_event_loop().stop()

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# --- Start bot here ---
async def main():
    await load_all_the_cogs()
    await the_bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        log.info("Bot shutting down due to keyboard interrupt...")
    except Exception as e:
        log.error("An error occurred during bot startup:", exc_info=True)
    finally:
        loop.close()
        log.info("Bot shutdown complete.")