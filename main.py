import asyncio
import aiofiles
import datetime


async def read_chat():
    reader, writer = await asyncio.open_connection('minechat.dvmn.org', 5000)
    while not reader.at_eof():
        message = await reader.readline()
        now = datetime.datetime.now()
        message_with_datetime = f'[{now.strftime("%d.%m.%y %H:%M")}] {message.decode()}'
        print(message_with_datetime, end='')
        async with aiofiles.open('chat.txt', 'a') as chatfile:
            await chatfile.write(message_with_datetime)

asyncio.run(read_chat())
