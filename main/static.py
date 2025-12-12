from discord.ext import commands
import os
from dotenv import load_dotenv
import discord

#СТАТИЧНЫЕ ЗНАЧЕНИЯ

load_dotenv()
TOKEN = os.getenv("TOKEN")
INSTRUCTIONS = os.getenv("INSTRUCTIONS")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "QWERTY!&UU")
DB_NAME = os.getenv("DB_NAME", "discord_bot")
DB_HOST = os.getenv("DB_HOST", "localhost")

guild_ids=[1440996306251153440]
PREFIX = "/"

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)