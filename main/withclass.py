import discord
from discord import option
from discord.ext import commands
from discord.ext.commands import check
import os
from dotenv import load_dotenv
import asyncio
from discord.errors import CheckFailure

load_dotenv()
TOKEN = os.getenv("TOKEN")
guild_ids=[1440996306251153440]
PREFIX = "/"

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

class User:
    def __init__(self, user_id, try_user_name, server_user_name: str, roles: list[str]):
        self.user_id = user_id
        self.try_user_name = try_user_name
        self.server_user_name = server_user_name
        self.roles = roles

    def __str__(self):
        return f"User({self.server_user_name})"

class CollManager:
    def __init__(self, bot):
        self.bot = bot

    async def create_channel(self, ctx, user: User, category_name: str):
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=category_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user.try_user_name: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        if discord.utils.get(guild.channels, name=user.server_user_name):
            await ctx.respond("❌ Канал с таким названием уже существует!")
            return None

        new_channel = await guild.create_text_channel(
            name=user.server_user_name,
            overwrites=overwrites,
            category=category
        )
        await ctx.respond(f"✔ Канал создан: {new_channel.mention}")
        return new_channel

    async def delete_channel(self, channel, server_user_name):
        await channel.send("Канал удалится через 3 секунды!")
        await asyncio.sleep(3)
        await channel.delete()


    async def run_coll_survey(self, ctx, channel):
        answers = {}

        def check(msg):
            return msg.author == ctx.author and msg.channel == channel

        # 1. Таймер
        options_timer = ["12", "14", "16", "18", "20"]
        await channel.send("Выберите вариант: `12`, `14`, `16`, `18`, `20`")

        while True:
            msg = await self.bot.wait_for("message", check=check)
            ans = msg.content.lower()
            if ans in options_timer:
                answers["timer"] = ans
                break
            await channel.send("❌ Неверный вариант. Попробуйте снова.")

        # 2. Где
        options_where = ["Статик", "Авалон", "Роум"]
        await channel.send("Выберите вариант: `Статик`, `Авалон`, `Роум`")

        while True:
            msg = await self.bot.wait_for("message", check=check)
            ans = msg.content
            if ans in options_where:
                answers["where"] = ans
                break
            await channel.send("❌ Неверный вариант. Попробуйте снова.")

        # 3. Сколько
        options_how = ["5", "7", "10", "12", "15", "20"]
        await channel.send("Выберите вариант: `5`, `7`, `10`, `12`, `15`, `20`")

        while True:
            msg = await self.bot.wait_for("message", check=check)
            ans = msg.content
            if ans in options_how:
                answers["howmany"] = ans
                break
            await channel.send("❌ Неверный вариант. Попробуйте снова.")

        await channel.send(f"Все ответы получены:\n{answers}")
        return answers

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    system_channel = member.guild.system_channel
    if system_channel:
        await system_channel.send(f"Welcome to our server, {member.mention}!")
        return

@bot.event
async def on_application_command_error(ctx, error):
    if isinstance(error, discord.errors.CheckFailure):
        print("error, pls comment this func")
        return
    raise error


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

@bot.slash_command(name="create_coll", description="Создание колла", guild_ids=guild_ids)
@has_role("User")
@in_category("col")
async def create_coll_c(ctx):

        user = User(
            user_id=ctx.author.id,
            try_user_name=ctx.author,
            server_user_name=ctx.author.display_name,
            roles=[role.name for role in ctx.author.roles]
        )

        manage = CollManager(bot)
        channel = await manage.create_channel(ctx, user,"col")
        if channel is None:
            return

        await manage.run_coll_survey(ctx, channel)

        await manage.delete_channel(channel, user.server_user_name)

print(2)
bot.run(TOKEN)