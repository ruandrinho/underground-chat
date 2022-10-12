import argparse
import asyncio
import logging
from contextlib import suppress

import anyio
from environs import Env

import gui_main
import minechat


async def main():
    logging.basicConfig(
        format='{asctime} - {name} - {levelname} - {message}',
        style='{',
        level=logging.INFO
    )
    watchdog_logger = logging.getLogger('minechat_watchdog')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(fmt='[{created:.0f}] {message}', style='{'))
    watchdog_logger.addHandler(stream_handler)

    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Underground chat with gui')
    parser.add_argument('--host', '-s', help='Host')
    parser.add_argument('--readingport', '-rp', type=int, help='Reading port')
    parser.add_argument('--writingport', '-wp', type=int, help='Writing port')
    parser.add_argument('--token', '-t', help='Chat token')
    parser.add_argument('--nickname', '-n', help='Chat nickname')
    parser.add_argument('--historyfile', '-f', help='File for history')
    args = parser.parse_args()

    config = {
        'host': args.host or env('HOST', default='minechat.dvmn.org'),
        'reading_port': args.readingport or env.int('READING_PORT', default=5000),
        'writing_port': args.writingport or env.int('WRITING_PORT', default=5050),
        'token': args.token or env('CHAT_TOKEN', default=''),
        'nickname': args.nickname or env('CHAT_NICKNAME', default=''),
        'history_file': args.historyfile or env('HISTORY_FILE', default='minechat.history'),
        'small_reconnect_timeout': env.int('SMALL_RECONNECT_TIMEOUT', default=3),
        'big_reconnect_timeout': env.int('BIG_RECONNECT_TIMEOUT', default=10)
    }

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    history_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    watchdog_queue = asyncio.Queue()

    await minechat.restore_messages(config['history_file'], messages_queue)

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(gui_main.draw, messages_queue, sending_queue, status_updates_queue)
            tg.start_soon(minechat.save_messages, config['history_file'], history_queue)
            tg.start_soon(
                minechat.handle_connection,
                config,
                messages_queue,
                sending_queue,
                history_queue,
                status_updates_queue,
                watchdog_queue
            )
    except minechat.InvalidToken:
        await gui_main.show_token_error()
    finally:
        tg.cancel_scope.cancel()


if __name__ == '__main__':
    with suppress(KeyboardInterrupt, gui_main.TkAppClosed):
        anyio.run(main)
