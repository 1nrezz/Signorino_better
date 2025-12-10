import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv("TOKEN")

guild_ids = [1440996306251153440]
PREFIX = "/"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# ===========================
# ✅ ОСНОВНОЙ КЛАСС БОТА
# ===========================
class CollBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=PREFIX, intents=intents)
        self.registered_slots = {}
        self.active_timers = {}


bot = CollBot()


# ===========================
# ✅ КНОПКИ
# ===========================
class SlotView(discord.ui.View):
    def __init__(self, bot: CollBot, message_id: int, max_slots: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.message_id = message_id

        for i in range(1, max_slots + 1):
            self.add_item(SlotButton(i))

        self.add_item(CancelButton())
        self.add_item(CloseButton())


class SlotButton(discord.ui.Button):
    def __init__(self, number: int):
        super().__init__(
            label=str(number),
            style=discord.ButtonStyle.success,
            custom_id=f"slot_{number}"
        )
        self.number = number

    async def callback(self, interaction: discord.Interaction):
        bot: CollBot = interaction.client
        slots = bot.registered_slots.get(interaction.message.id)

        if not slots:
            await interaction.response.send_message("❌ Слоты не найдены!", ephemeral=True)
            return

        user = interaction.user

        if slots[self.number] is not None:
            await interaction.response.send_message("❌ Это место уже занято!", ephemeral=True)
            return

        if user.mention in slots.values():
            await interaction.response.send_message("❌ Вы уже записаны!", ephemeral=True)
            return

        slots[self.number] = user.mention
        await update_message(interaction.message, slots)

        await interaction.response.send_message(
            f"✅ Вы записаны на {self.number})",
            ephemeral=True
        )


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="❌ Отменить запись",
            style=discord.ButtonStyle.danger
        )

    async def callback(self, interaction: discord.Interaction):
        bot: CollBot = interaction.client
        slots = bot.registered_slots.get(interaction.message.id)
        user = interaction.user

        removed = False

        for key in slots:
            if slots[key] == user.mention:
                slots[key] = None
                removed = True

        if not removed:
            await interaction.response.send_message("❌ Вы не были записаны.", ephemeral=True)
            return

        await update_message(interaction.message, slots)
        await interaction.response.send_message("✅ Запись отменена!", ephemeral=True)


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🔒 Закрыть",
            style=discord.ButtonStyle.secondary
        )

    async def callback(self, interaction: discord.Interaction):
        await close_coll(interaction.message)


# ===========================
# ✅ ОБНОВЛЕНИЕ СООБЩЕНИЯ
# ===========================
async def update_message(message, slots):
    lines = "\n".join(f"{i}) {slots[i] or ''}" for i in slots)

    new_text = (
        message.content.split("ЗАПОЛНЯЕМ")[0] +
        "ЗАПОЛНЯЕМ РОЛИ:\n\n" +
        lines
    )

    await message.edit(content=new_text)


# ===========================
# ✅ ЗАКРЫТИЕ + ПИНГ ВСЕХ
# ===========================
async def close_coll(message):
    bot: CollBot = message.channel.guild._state._get_client()

    slots = bot.registered_slots.get(message.id)
    if not slots:
        return

    mentions = [v for v in slots.values() if v]

    ping_text = " ".join(mentions) if mentions else "Никто не записался."

    await message.edit(view=None)
    await message.reply(f"✅ Сбор закрыт!\n{ping_text}")

    bot.registered_slots.pop(message.id, None)


# ===========================
# ✅ АВТОТАЙМЕР ЗАКРЫТИЯ
# ===========================
async def auto_close(message, seconds):
    await asyncio.sleep(seconds)
    await close_coll(message)


# ===========================
# ✅ ОТПРАВКА КОЛЛА
# ===========================
async def send_coll(ctx, channel_name: str, answers: dict):
    guild = ctx.guild
    timer = answers["timer"]
    where = answers["where"]
    howmany = int(answers["howmany"])

    timer_category = discord.utils.get(guild.categories, name="таймера")
    timer_channel = discord.utils.get(timer_category.text_channels, name=channel_name)

    await timer_channel.send(f"Колл {ctx.author.mention} → {timer}")

    user_category = discord.utils.get(guild.categories, name=timer)
    user_channel = discord.utils.get(user_category.text_channels, name=channel_name)

    slots = {i: None for i in range(1, howmany + 1)}

    text = (
        f"### Новый колл от {ctx.author.mention}\n"
        f"**Время:** {timer}\n"
        f"**Куда:** {where}\n\n"
        f"ЗАПОЛНЯЕМ РОЛИ\n\n" +
        "\n".join(f"{i})" for i in slots)
    )

    message = await user_channel.send(text)

    bot.registered_slots[message.id] = slots

    view = SlotView(bot, message.id, howmany)
    await message.edit(view=view)

    # ✅ АВТОЗАКРЫТИЕ ЧЕРЕЗ 5 МИНУТ (300 сек)
    asyncio.create_task(auto_close(message, 300))


# ===========================
# ✅ КОМАНДА
# ===========================
@bot.slash_command(name="create_coll", description="Создать колл", guild_ids=guild_ids)
async def create_coll(ctx):
    answers = {
        "timer": "18",
        "where": "Статик",
        "howmany": "5"
    }

    await ctx.respond("✅ Колл создан!")
    await send_coll(ctx, "сбор", answers)


# ===========================
# ✅ ЗАПУСК
# ===========================
@bot.event
async def on_ready():
    print(f"✅ Бот запущен: {bot.user}")


bot.run(TOKEN)
