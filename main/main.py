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

@bot.slash_command(name="member_join", description="Login in server", guild_ids=guild_ids)
async def member_join_c(ctx):
    user = ctx.author.mention
    await ctx.respond(f"Welcom to our server {user}")
    login_channel = discord.utils.get(ctx.guild.channels, name="welcome")
    if login_channel and isinstance(login_channel, discord.TextChannel):
        await login_channel.send(f"Welcome to our server, {user}!")
    else:
        await ctx.send("System channel 'welcome' not found!")

@bot.event
async def member_join(member):
    login_channel = discord.utils.get(member.guild.channels, name="welcome")
    if login_channel:
        await login_channel.send(f"Welcome to our server, {member.mention}!")


bot.run(TOKEN)