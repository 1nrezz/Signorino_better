import discord
from discord import option
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

@bot.event
async def on_member_join(member):
    login_channel = discord.utils.get(member.guild.channels, name="welcome")
    if login_channel:
        await login_channel.send(f"Welcome to our server, {member.mention}!")
        return

@bot.event
async def create_channel(ctx, name: str):
    guild = ctx.guild

    if discord.utils.get(guild.channels, name=name):
        await ctx.respond("❌ Канал с таким названием уже существует!")
        return

    new_channel = await guild.create_text_channel(name=name)
    await ctx.respond(f"✔ Канал создан: {new_channel.mention}")
    return
#####


@bot.slash_command(name="member_join", description="Login in server", guild_ids=guild_ids)
async def member_join_c(ctx):
    user = ctx.author.mention
    await ctx.respond(f"Welcom to our server {user}")
    login_channel = discord.utils.get(ctx.guild.channels, name="welcome")
    if login_channel and isinstance(login_channel, discord.TextChannel):
        await login_channel.send(f"Welcome to our server, {user}!")
    else:
        await ctx.send("System channel 'welcome' not found!")


@bot.slash_command(name="create_coll", description="Создание колла", guild_ids=guild_ids)
async def create_coll_c(ctx):
    answers = {}
    user = ctx.author.mention
    await ctx.respond(f"Создание кола для {user}")

    #first
    options_timer = ["12", "14", "16", "18", "20"]
    def check(msg):
        return (
                msg.author == ctx.author and
                msg.channel == ctx.channel
        )

    await ctx.respond(
        "Выберите вариант: `12`, `14`, `16`, `18`, `20`"
    )

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content.lower()

        if answer in options_timer:
            answers["timer"] = answer
            break
        else:
            await ctx.send("❌ Неверный вариант. Попробуйте снова.")


    #second
    options_where = ["Статик", "Авалон", "Роум"]

    await ctx.respond(
        "Выберите вариант: `Статик`, `Авалон`, `Роум`"
    )

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content

        if answer in options_where:
            answers["where"] = answer
            break
        else:
            await ctx.send("❌ Неверный вариант. Попробуйте снова.")

    #third
    options_howMany = ["5", "7", "10", "12", "15", "20"]

    await ctx.respond(
        "Выберите вариант: `5`, `7`, `10`, `12`, `15`, `20`"
    )

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content.lower()

        if answer in options_howMany:
            answers["howmany"] = answer
            break
        else:
            await ctx.send("❌ Неверный вариант. Попробуйте снова.")

    await ctx.send(f"Все ответы получены:\n{answers}")

    await create_channel(ctx, f"Timer{answers['timer']}")
    return


bot.run(TOKEN)