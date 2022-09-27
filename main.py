import argparse
import asyncio
import logging
import gui
import time
from pathlib import Path

import aiofiles
from environs import Env

from minechat_utils import get_minechat_connection

logger = logging.getLogger(__name__)


async def generate_msgs(queue):
    while True:
        queue.put_nowait(round(time.time()))
        await asyncio.sleep(1)


async def read_messages(host, port, messages_queue, history_queue):
    async with get_minechat_connection(host, port) as (reader, writer):
        while not reader.at_eof():
            message = await reader.readline()
            message = message.decode().strip()
            messages_queue.put_nowait(message)
            history_queue.put_nowait(message)


async def save_messages(filepath, history_queue):
    async with aiofiles.open(filepath, 'a', encoding='utf-8') as chatfile:
        while True:
            message = await history_queue.get()
            await chatfile.write(f'{message}\n')


async def restore_messages(filepath, messages_queue):
    if not Path(filepath).exists():
        return
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as chatfile:
        history = await chatfile.read()
        messages_queue.put_nowait(history)


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
    history_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    await restore_messages(config['history_file'], messages_queue)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        await asyncio.gather(
            gui.draw(messages_queue, sending_queue, status_updates_queue),
            read_messages(config['host'], config['reading_port'], messages_queue, history_queue),
            save_messages(config['history_file'], history_queue)
        )
    )


if __name__ == '__main__':
    asyncio.run(main())
