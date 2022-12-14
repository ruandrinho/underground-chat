import argparse
import asyncio
import datetime

import aiofiles
from environs import Env

from minechat import get_connection


async def read_chat(host, port, history_file):
    async with (
        aiofiles.open(history_file, 'a') as chatfile,
        get_connection(host, port) as (reader, writer)
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
        'host': args.host or env('HOST', default='minechat.dvmn.org'),
        'port': args.port or env.int('READING_PORT', default=5000),
        'history_file': args.historyfile or env('HISTORY_FILE', default='minechat.history')
    }

    asyncio.run(read_chat(**minechat_config))


if __name__ == '__main__':
    main()
