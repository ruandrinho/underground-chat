import argparse
import asyncio
import datetime

import aiofiles
from environs import Env


async def parse_minechat(host, port, history_file):
    reader, writer = await asyncio.open_connection(host, port)
    while not reader.at_eof():
        message = await reader.readline()
        now = datetime.datetime.now()
        message_with_datetime = f'[{now.strftime("%d.%m.%y %H:%M")}] {message.decode()}'
        print(message_with_datetime, end='')
        async with aiofiles.open(history_file, 'a') as chatfile:
            await chatfile.write(message_with_datetime)


def main():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Read chat and save messages to file')
    parser.add_argument('--host', '-s', action='store', help='Host')
    parser.add_argument('--port', '-p', type=int, action='store', help='Port')
    parser.add_argument('--historyfile', '-f', action='store', help='File for history')
    args = parser.parse_args()

    minechat_config = {
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'port': args.port if args.port else env.int('PORT', default=5000),
        'history_file': args.historyfile if args.historyfile else env('HISTORY_FILE', default='minechat.history')
    }

    asyncio.run(parse_minechat(**minechat_config))


if __name__ == '__main__':
    main()
