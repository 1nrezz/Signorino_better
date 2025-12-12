import static

#ТРЕДЫ

async def create_thread(message):
    thread = await message.create_thread(
        name="запись",
        auto_archive_duration=1440,
    )
    await thread.send(static.INSTRUCTIONS) #instruction
    return thread