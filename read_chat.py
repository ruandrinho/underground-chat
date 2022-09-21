import argparse
import asyncio
import datetime
from contextlib import asynccontextmanager

import aiofiles
from environs import Env


@asynccontextmanager
async def get_minechat_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def read_chat(host, port, history_file):
    async with (
        aiofiles.open(history_file, 'a') as chatfile,
        get_minechat_connection(host, port) as (reader, writer)
    ):
        while not reader.at_eof():
            message = await reader.readline()
            now = datetime.datetime.now()
            message_with_datetime = f'[{now.strftime("%d.%m.%y %H:%M")}] {message.decode()}'
            print(message_with_datetime, end='')
            await chatfile.write(message_with_datetime)


def main():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Read chat and save messages to file')
    parser.add_argument('--host', '-s', help='Host')
    parser.add_argument('--port', '-p', type=int, help='Port')
    parser.add_argument('--historyfile', '-f', help='File for history')
    args = parser.parse_args()

    minechat_config = {
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'port': args.port if args.port else env.int('READING_PORT', default=5000),
        'history_file': args.historyfile if args.historyfile else env('HISTORY_FILE', default='minechat.history')
    }

    asyncio.run(read_chat(**minechat_config))


if __name__ == '__main__':
    main()
