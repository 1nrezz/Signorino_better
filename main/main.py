import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
guild_ids=[1440996306251153440]
PREFIX = "/"

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.slash_command(name="ping", description="Проверка бота", guild_ids=guild_ids)
async def ping(ctx):
    await ctx.respond("ping!")
    await ctx.send("Pong!")

bot.run(TOKEN)