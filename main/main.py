import discord
from discord import option
from discord.ext import commands
from discord.ext.commands import check
import os
from dotenv import load_dotenv
import asyncio

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
    system_channel = member.guild.system_channel
    if system_channel:
        await system_channel.send(f"Welcome to our server, {member.mention}!")
        return

def has_role(role_name: str):
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=role_name)
        return role is not None
    return check(predicate)

def in_category(category_name: str):
    async def predicate(ctx):
        if ctx.channel.category and ctx.channel.category.name == category_name:
            return True
        return False
    return check(predicate)

async def create_channel(ctx, name, category_name: str):
    guild = ctx.guild
    user = discord.utils.get(guild.members, name=name)
    category = discord.utils.get(ctx.guild.categories, name=category_name)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    if user:
        overwrites[user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    if discord.utils.get(guild.channels, name=name):
        await ctx.respond("❌ Канал с таким названием уже существует!")
        return

    new_channel = await guild.create_text_channel(name=name, overwrites = overwrites, category = category)
    await ctx.respond(f"✔ Канал создан: {new_channel.mention}")
    return new_channel

async def delete_coll(ctx, name):
    guild = ctx.guild
    await ctx.send("Канал удалиться через 3 секунды!")
    channel = discord.utils.get(guild.text_channels, name=name)
    await asyncio.sleep(3)
    await channel.delete()
    return

#####


# @bot.slash_command(name="member_join", description="Login in server", guild_ids=guild_ids)
# async def member_join_c(ctx):
#     user = ctx.author.mention
#     await ctx.respond(f"Welcom to our server {user}")
#     login_channel = discord.utils.get(ctx.guild.channels, name="welcome")
#     if login_channel and isinstance(login_channel, discord.TextChannel):
#         await login_channel.send(f"Welcome to our server, {user}!")
#     else:
#         await ctx.send("System channel 'welcome' not found!")


##### , category = category


@bot.slash_command(name="create_coll", description="Создание колла", guild_ids=guild_ids)
@has_role("User")
@in_category("col")
async def create_coll_c(ctx):
    answers = {}
    user = ctx.author.mention
    await ctx.respond(f"Создание кола для {user}")

    name = ctx.author.display_name
    category_name = "col"
    new_channel = await create_channel(ctx, name, category_name)

    if new_channel == None:
        return

    def check(msg):
        return (
                msg.author == ctx.author and
                msg.channel == new_channel
        )

    #first
    options_timer = ["12", "14", "16", "18", "20"]

    await new_channel.send("Выберите вариант: `12`, `14`, `16`, `18`, `20`")

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content.lower()

        if answer in options_timer:
            answers["timer"] = answer
            break
        else:
            await new_channel.send("❌ Неверный вариант. Попробуйте снова.")


    #second
    options_where = ["Статик", "Авалон", "Роум"]

    await new_channel.send("Выберите вариант: `Статик`, `Авалон`, `Роум`")

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content

        if answer in options_where:
            answers["where"] = answer
            break
        else:
            await new_channel.send("❌ Неверный вариант. Попробуйте снова.")

    #third
    options_howMany = ["5", "7", "10", "12", "15", "20"]

    await new_channel.send("Выберите вариант: `5`, `7`, `10`, `12`, `15`, `20`")

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content.lower()

        if answer in options_howMany:
            answers["howmany"] = answer
            break
        else:
            await new_channel.send("❌ Неверный вариант. Попробуйте снова.")

    await new_channel.send(f"Все ответы получены:\n{answers}")
    await delete_coll(new_channel, name)
    return

bot.run(TOKEN)