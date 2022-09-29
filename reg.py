import argparse
import asyncio
from contextlib import suppress

import anyio
from environs import Env

import gui_reg
from minechat import get_minechat_connection, sign_up, save_token


async def watch_events(config, events_queue):
    while True:
        nickname = await events_queue.get()
        async with get_minechat_connection(config['host'], config['writing_port']) as (reader, writer):
            credentials = await sign_up(reader, writer, nickname, send_blank=True)
        await save_token(credentials['nickname'], credentials['account_hash'])
        await gui_reg.show_success(credentials['nickname'])


async def main():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Registration in underground chat')
    parser.add_argument('--host', '-s', help='Host')
    parser.add_argument('--writingport', '-wp', type=int, help='Writing port')
    args = parser.parse_args()

    config = {
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'writing_port': args.writingport if args.writingport else env.int('WRITING_PORT', default=5050)
    }

    events_queue = asyncio.Queue()

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(gui_reg.draw, events_queue)
            tg.start_soon(watch_events, config, events_queue)
    finally:
        tg.cancel_scope.cancel()


if __name__ == '__main__':
    with suppress(KeyboardInterrupt, gui_reg.TkAppClosed):
        anyio.run(main)
