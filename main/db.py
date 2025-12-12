import asyncpg
import asyncio
import discord
from discord.ui import View, Button
import threads
import static

db_pool: asyncpg.pool.Pool = None

#СОЗДАНИЕ И ПРОВЕРКА ДБ

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user = static.DB_USER,
        password = static.DB_PASSWORD,
        database = static.DB_NAME,
        host = static.DB_HOST
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

        await conn.execute("""
                ALTER TABLE call_slots
                ADD COLUMN IF NOT EXISTS user_id BIGINT
            """)

        await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'call_slots_unique_per_call'
                    ) THEN
                        ALTER TABLE call_slots
                        ADD CONSTRAINT call_slots_unique_per_call
                        UNIQUE (call_id, user_id);
                    END IF;
                END $$;
            """)


#КЛАСС ДЛЯ МЕНЮ КНОПКИ

class ChoiceView(View):
    def __init__(self, options, user_id, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.value = None
        self.user_id = user_id

        for option in options:
            btn = Button(label=str(option), style=discord.ButtonStyle.primary, custom_id=str(option))
            btn.callback = self._make_callback(option)
            self.add_item(btn)

    def _make_callback(self, option):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не твой выбор!", ephemeral=True)
                return

            self.value = option
            await interaction.response.defer()
            self.stop()
        return callback


class CancelButton(Button):
    def __init__(self, call_id):
        super().__init__(label="Отменить запись", style=discord.ButtonStyle.danger)
        self.call_id = call_id

    async def callback(self, interaction):
        async with db_pool.acquire() as conn:
            user_slot = await conn.fetchrow(
                "SELECT slot_number FROM call_slots WHERE call_id = $1 AND user_id = $2",
                self.call_id, interaction.user.id
            )
            if not user_slot:
                return await interaction.response.send_message("❌ Вы не записаны на этот колл.", ephemeral=True)

            await conn.execute(
                "DELETE FROM call_slots WHERE call_id = $1 AND user_id = $2",
                self.call_id, interaction.user.id
            )

        await interaction.response.send_message("❌ Вы отменили запись.", ephemeral=True)
        await update_call_message(self.call_id, interaction.message)

class CancelCall(Button):
    def __init__(self, call_id, creator_id):
        super().__init__(label="❌ Отменить колл", style=discord.ButtonStyle.danger)
        self.call_id = call_id
        self.creator_id = creator_id

    async def callback(self, interaction):
        if interaction.user.id != self.creator_id:
            return await interaction.response.send_message(
                "❌ Только создатель может отменить колл.",
                ephemeral=True
            )

        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM calls WHERE id = $1", self.call_id)

        await interaction.message.delete()
        await interaction.response.send_message("Колл отменён.", ephemeral=True)


async def update_call_message(call_id, message):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT max_slots FROM calls WHERE id = $1", call_id)
        if not row:
            return

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

async def get_slot_view(call_id, user_id, creator_id):
    view = View()
    async with db_pool.acquire() as conn:
        user_slot = await conn.fetchval(
            "SELECT 1 FROM call_slots WHERE call_id=$1 AND user_id=$2",
            call_id, user_id
        )
    if user_slot:
        view.add_item(CancelButton(call_id))
    if user_id == creator_id:
        view.add_item(CancelCall(call_id, creator_id))
    return view

async def edit_message(message, thread, call_id, creator_id):
    while True:
        view = await get_slot_view(call_id, creator_id, creator_id)
        await message.edit(view=view)

        def check(m):
            return m.channel == thread and not m.author.bot

        msg = await static.bot.wait_for("message", check=check)
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

            user_slot = await conn.fetchrow(
                "SELECT slot_number FROM call_slots WHERE call_id = $1 AND user_id = $2",
                call_id, msg.author.id
            )

            if user_slot:
                await conn.execute(
                    "UPDATE call_slots SET slot_number = $3 WHERE call_id = $1 AND user_id = $2",
                    call_id, msg.author.id, slot_number
                )
            else:
                taken = await conn.fetchrow(
                    "SELECT user_id FROM call_slots WHERE call_id = $1 AND slot_number = $2",
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
        await update_call_message(call_id, message)
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

    thread = await threads.create_thread(full_message)

    asyncio.create_task(edit_message(full_message, thread, call_id, ctx.author.id))

    return full_message, thread