import asyncio


async def read_chat():
    reader, writer = await asyncio.open_connection('minechat.dvmn.org', 5000)
    while not reader.at_eof():
        data = await reader.readline()
        print(data.decode())

asyncio.run(read_chat())
