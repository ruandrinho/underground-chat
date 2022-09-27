import argparse
import asyncio
import logging
import gui
import time

import aiofiles
from environs import Env

from minechat_utils import get_minechat_connection

logger = logging.getLogger(__name__)


async def generate_msgs(queue):
    while True:
        queue.put_nowait(round(time.time()))
        await asyncio.sleep(1)


async def read_msgs(host, port, queue):
    async with (
        # aiofiles.open(history_file, 'a') as chatfile,
        get_minechat_connection(host, port) as (reader, writer)
    ):
        while not reader.at_eof():
            message = await reader.readline()
            queue.put_nowait(message.decode().strip())
            # now = datetime.datetime.now()
            # message_with_datetime = f'[{now.strftime("%d.%m.%y %H:%M")}] {message.decode()}'
            # print(message_with_datetime, end='')
            # await chatfile.write(message_with_datetime)


async def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Underground chat with GUI')
    parser.add_argument('--host', '-s', help='Host')
    parser.add_argument('--readingport', '-rp', type=int, help='Reading port')
    parser.add_argument('--writingport', '-wp', type=int, help='Writing port')
    parser.add_argument('--token', '-t', help='Chat token')
    parser.add_argument('--nickname', '-n', help='Chat nickname')
    parser.add_argument('--historyfile', '-f', help='File for history')
    args = parser.parse_args()

    config = {
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'reading_port': args.readingport if args.readingport else env.int('READING_PORT', default=5000),
        'writing_port': args.writingport if args.writingport else env.int('WRITING_PORT', default=5050),
        'token': args.token if args.token else env('CHAT_TOKEN', default=''),
        'nickname': args.nickname if args.nickname else env('CHAT_NICKNAME', default=''),
        'history_file': args.historyfile if args.historyfile else env('HISTORY_FILE', default='minechat.history')
    }

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        await asyncio.gather(
            gui.draw(messages_queue, sending_queue, status_updates_queue),
            read_msgs(config['host'], config['reading_port'], messages_queue)
        )
    )


if __name__ == '__main__':
    asyncio.run(main())
