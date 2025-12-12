import discord
import asyncio
import db
import decorators
import static

#ДЕФОЛТ КОМАНДЫ

@static.bot.event
async def on_ready():
    await db.init_db()
    print(f"Logged in as {static.bot.user}")

@static.bot.event
async def on_member_join(member):
    system_channel = member.guild.system_channel
    if system_channel:
        await system_channel.send(f"Welcome to our server, {member.mention}!")
        return

@static.bot.event
async def on_application_command_error(error):
    if isinstance(error, discord.errors.CheckFailure):
        print("error, pls comment this func")
        return
    raise error

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

async def helper_manage_coll(ctx, channel, options):
    view = db.ChoiceView(options, ctx.author.id, timeout=120)
    await channel.send("Выберите время:", view=view)
    await view.wait()

    if view.value is None:
        await channel.send("⏳ Время истекло.")
        return None

    return view.value


async def manage_coll(ctx, channel):
    answers = {}
    # 1 → выбор времени
    options_timer = ["12", "14", "16", "18", "20"]
    answers["timer"] = await helper_manage_coll(ctx, channel, options_timer)
    if answers["timer"] is None:
        return None

    # 2 → выбор куда
    options_where = ["Статик", "Авалон", "Роум"]
    answers["where"] = await helper_manage_coll(ctx, channel, options_where)
    if answers["where"] is None:
        return None

    # 3 → выбор количества
    options_howmany = ["5", "7", "10", "12", "15", "20"]
    answers["howmany"] = await helper_manage_coll(ctx, channel, options_howmany)
    if answers["howmany"] is None:
        return None

    return answers

@static.bot.slash_command(name="create_coll", description="Создание колла", guild_ids=static.guild_ids)
@decorators.has_role("User")
@decorators.in_category("col")
async def create_coll(ctx):
    user_id = ctx.author.mention
    await ctx.respond(f"Создание кола для {user_id}")

    server_user_name = ctx.author.display_name
    try_user_name = ctx.author
    category_name = "col"

    new_channel = await create_coll_channel(ctx, server_user_name, category_name, try_user_name)

    answers = await manage_coll(ctx, new_channel)

    await new_channel.send(f"Все ответы получены:\n{answers}")
    await delete_coll(new_channel, server_user_name)

    send_channel = "сбор"
    await db.send_coll(ctx, send_channel, answers)

    return

print(1)
static.bot.run(static.TOKEN)