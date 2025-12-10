import discord
from discord.ext import commands
from discord.ext.commands import check
import os
from dotenv import load_dotenv
import asyncio
import asyncpg

load_dotenv()
TOKEN = os.getenv("TOKEN")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "QWERTY!&UU")
DB_NAME = os.getenv("DB_NAME", "discord_bot")
DB_HOST = os.getenv("DB_HOST", "localhost")

guild_ids=[1440996306251153440]
PREFIX = "/"

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

#СОЗДАНИЕ И ПРОВЕРКА ДБ

db_pool: asyncpg.pool.Pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user = DB_USER,
        password = DB_PASSWORD,
        database = DB_NAME,
        host = DB_HOST
    )

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id SERIAL PRIMARY KEY,
                creator_id BIGINT,
                message_id BIGINT,
                timer TEXT,
                place TEXT,
                max_slots INT,
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS call_slots (
                id SERIAL PRIMARY KEY,
                call_id INT REFERENCES calls(id) ON DELETE CASCADE,
                slot_number INT
            )
        """)

        user_id_column = await conn.fetchval("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='call_slots' AND column_name='user_id'
                """)
        if not user_id_column:
            await conn.execute("""
                        ALTER TABLE call_slots
                        ADD COLUMN user_id BIGINT UNIQUE
                    """)

#ДЕФОЛТ КОМАНДЫ

@bot.event
async def on_ready():
    await init_db()
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

#ДЕКОРАТОРЫ

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

#ФУНКЦИИ СОЗДАНИЯ КАНАЛОВ

async def create_coll_channel(ctx, server_user_name: str, category_name: str, try_user_name):
    guild = ctx.guild

    in_category = discord.utils.get(guild.categories, name=category_name)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        try_user_name: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    if try_user_name:
        overwrites[try_user_name] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    if discord.utils.get(guild.channels, name=server_user_name):
        await ctx.respond("❌ Канал с таким названием уже существует!")
        return

    new_channel = await guild.create_text_channel(name=server_user_name, overwrites = overwrites, category = in_category)
    await ctx.respond(f"✔ Канал создан: {new_channel.mention}")
    return new_channel

async def delete_coll(ctx, server_user_name):
    guild = ctx.guild
    await ctx.send("Канал удалиться через 3 секунды!")
    channel = discord.utils.get(guild.text_channels, name=server_user_name)
    await asyncio.sleep(3)
    await channel.delete()
    return

async def manage_coll(ctx, channel):
    answers = {}
    def check(msg):
        return msg.author == ctx.author and msg.channel == channel

    # first
    options_timer = ["12", "14", "16", "18", "20"]

    await channel.send("Выберите вариант: `12`, `14`, `16`, `18`, `20`")

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content.lower()

        if answer in options_timer:
            answers["timer"] = answer
            break
        else:
            await channel.send("❌ Неверный вариант. Попробуйте снова.")

    # second
    options_where = ["Статик", "Авалон", "Роум"]

    await channel.send("Выберите вариант: `Статик`, `Авалон`, `Роум`")

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content

        if answer in options_where:
            answers["where"] = answer
            break
        else:
            await channel.send("❌ Неверный вариант. Попробуйте снова.")

    # third
    options_howMany = ["5", "7", "10", "12", "15", "20"]

    await channel.send("Выберите вариант: `5`, `7`, `10`, `12`, `15`, `20`")

    while True:
        msg = await bot.wait_for("message", check=check)
        answer = msg.content.lower()

        if answer in options_howMany:
            answers["howmany"] = answer
            break
        else:
            await channel.send("❌ Неверный вариант. Попробуйте снова.")
    return answers

async def create_thread(message):
    thread = await message.create_thread(
        name="запись",
        auto_archive_duration=1440,
    )
    await thread.send("Введите цифру") #instruction
    return thread

async def edit_message(message, thread, call_id):
    def check(m):
        return m.channel == thread and not m.author.bot

    while True:
        msg = await bot.wait_for("message", check=check)
        content = msg.content.strip()

        if not content.isdigit():
            await thread.send("❌ Введите только число!")
            continue

        slot_number = int(content)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT max_slots FROM calls WHERE id = $1", call_id
            )
            if not row or slot_number < 1 or slot_number > row["max_slots"]:
                await thread.send("❌ Нет такого слота!")
                continue

            exists = await conn.fetchrow(
                "SELECT * FROM call_slots WHERE call_id = $1 AND user_id = $2",
                call_id, msg.author.id
            )

            if exists:
                await conn.execute(
                    "DELETE FROM call_slots WHERE call_id = $1 AND user_id = $2",
                    call_id, msg.author.id
                )
                await thread.send(f"❌ {msg.author.mention} снялся с колла.")
            else:
                taken = await conn.fetchrow(
                    "SELECT * FROM call_slots WHERE call_id = $1 AND slot_number = $2",
                    call_id, slot_number
                )
                if taken:
                    await thread.send("❌ Этот слот уже занят!")
                    continue
                await conn.execute(
                    "INSERT INTO call_slots (call_id, slot_number, user_id) VALUES ($1, $2, $3)",
                    call_id, slot_number, msg.author.id
                )
                await thread.send(f"✔ {msg.author.mention} записан на слот {slot_number}")

            slots = await conn.fetch(
                "SELECT slot_number, user_id FROM call_slots WHERE call_id=$1 ORDER BY slot_number", call_id
            )

            max_slots = row["max_slots"]
            lines = []
            slots_dict = {s["slot_number"]: s["user_id"] for s in slots}

            for i in range(1, max_slots + 1):
                if i in slots_dict:
                    lines.append(f"{i}: <@{slots_dict[i]}>")
                else:
                    lines.append(f"{i})")
            new_text = f"### Новый колл\n\n{chr(10).join(lines)}"
            await message.edit(content=new_text)
    return

async def send_coll(ctx, channel: str, answers: dict):
    guild = ctx.guild
    timer = answers["timer"]
    where = answers["where"]
    howmany = int(answers["howmany"])

    name_timer = "таймера"

    # ---1

    timer_category = discord.utils.get(guild.categories, name=name_timer)
    timer_channel = discord.utils.get(timer_category.text_channels, name=channel)
    short_msg = f"Колл {ctx.author.mention} → {timer}"

    await timer_channel.send(short_msg)

    # ---2

    user_category = discord.utils.get(guild.categories, name=timer)
    user_channel = discord.utils.get(user_category.text_channels, name=channel)

    lines = []
    for i in range(1, howmany + 1):
        lines.append(f"{i})")
    numbered_list = "\n".join(lines)

    full_msg = (
        f"### Новый колл от {ctx.author.mention}\n"
        f"**Время:** {timer}\n"
        f"**Куда:** {where}\n"
        f"\nЗАПОЛНЯЕМ РОЛИ\n\n"
        f"{numbered_list}\n"
    )

    full_message = await user_channel.send(full_msg)

    async with db_pool.acquire() as conn:
        call_id = await conn.fetchval(
            "INSERT INTO calls(creator_id, message_id, timer, place, max_slots) VALUES($1,$2,$3,$4,$5) RETURNING id",
            ctx.author.id, full_message.id, timer, where, howmany
        )

    thread = await create_thread(full_message)

    asyncio.create_task(edit_message(full_message, thread, call_id))

    return full_message, thread

@bot.slash_command(name="create_coll", description="Создание колла", guild_ids=guild_ids)
@has_role("User")
@in_category("col")
async def create_coll(ctx):
    user_id = ctx.author.mention
    await ctx.respond(f"Создание кола для {user_id}")

    server_user_name = ctx.author.display_name
    try_user_name = ctx.author
    category_name = "col"

    new_channel = await create_coll_channel(ctx, server_user_name, category_name, try_user_name)

    if new_channel == None:
        return

    answers = await manage_coll(ctx, new_channel)

    await new_channel.send(f"Все ответы получены:\n{answers}")
    await delete_coll(new_channel, server_user_name)

    send_channel = "сбор"
    await send_coll(ctx, send_channel, answers)

    return

print(1)
bot.run(TOKEN)
