import argparse
import asyncio
import json
import logging
import socket
from contextlib import suppress
from pathlib import Path

import aiofiles
import anyio
from async_timeout import timeout
from environs import Env

import gui
from minechat_utils import get_minechat_connection

SMALL_RECONNECT_TIMEOUT = 3
BIG_RECONNECT_TIMEOUT = 10


def get_info_logger(name, format):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(logging.Formatter(fmt=format, style='{'))
    logger.addHandler(logger_sh)
    return logger


logger = get_info_logger(__name__, '{asctime} - {name} - {levelname} - {message}')
watchdog_logger = get_info_logger('watchdog', '[{created:.0f}] {message}')


class InvalidToken(Exception):
    pass


async def handle_connection(config, messages_queue, sending_queue, history_queue, status_updates_queue, watchdog_queue):
    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(read_messages, config['host'], config['reading_port'],
                          messages_queue, history_queue, status_updates_queue, watchdog_queue)
            tg.start_soon(send_messages, config['host'], config['writing_port'], config['token'], config['nickname'],
                          sending_queue, messages_queue, status_updates_queue, watchdog_queue)
            tg.start_soon(watch_for_connection, watchdog_queue)
    except (ConnectionError, socket.gaierror, anyio.ExceptionGroup) as exception:
        tg.cancel_scope.cancel()
        if exception.__class__.__name__ != 'ConnectionError':
            logger.info('Reconnecting with timeout')
            await anyio.sleep(BIG_RECONNECT_TIMEOUT)
        else:
            logger.info('Reconnecting')
        await handle_connection(
            config,
            messages_queue,
            sending_queue,
            history_queue,
            status_updates_queue,
            watchdog_queue
        )


async def receive_credentials(reader):
    credentials_response = await reader.readline()
    credentials = json.loads(credentials_response.decode().strip())
    logger.info(f'Received {credentials}')
    return credentials


async def save_token(nickname, token):
    async with aiofiles.open(f'{nickname}.token', 'w') as tokenfile:
        await tokenfile.write(token)


async def sign_in(reader, writer, token):
    logger.info(f'Sending "{token}"')
    await write_to_chat(writer, f'{token}\n')
    return await receive_credentials(reader)


async def sign_up(reader, writer, nickname, send_blank=False):
    if send_blank:
        await write_to_chat(writer, '\n')
    nickname_query = await reader.readline()
    logger.info(nickname_query.decode().strip())
    logger.info(f'Sending "{nickname}"')
    await write_to_chat(writer, f'{nickname}\n')
    return await receive_credentials(reader)


async def submit_message(writer, message):
    message = message.replace('\n', ' ')
    await write_to_chat(writer, f'{message}\n\n')


async def write_to_chat(writer, message):
    writer.write(message.encode())
    await writer.drain()


async def read_messages(host, port, messages_queue, history_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    async with get_minechat_connection(host, port) as (reader, writer):
        while not reader.at_eof():
            try:
                async with timeout(SMALL_RECONNECT_TIMEOUT) as cm:
                    message = await reader.readline()
                    message = message.decode().strip()
                    messages_queue.put_nowait(message)
                    history_queue.put_nowait(message)
                    watchdog_queue.put_nowait('New message in chat')
                    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            except asyncio.TimeoutError:
                if cm.expired:
                    watchdog_queue.put_nowait('1s timeout is elapsed')


async def send_messages(
        host, port, token, nickname, sending_queue, messages_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    async with get_minechat_connection(host, port) as (reader, writer):
        greeting_query = await reader.readline()
        logger.info(greeting_query.decode().strip())

        credentials = await sign_in(reader, writer, token)
        if credentials is None:
            raise InvalidToken
        messages_queue.put_nowait(f'Выполнена авторизация. Пользователь {credentials["nickname"]}')
        event = gui.NicknameReceived(credentials['nickname'])
        status_updates_queue.put_nowait(event)

        while True:
            try:
                async with timeout(SMALL_RECONNECT_TIMEOUT) as cm:
                    message = await sending_queue.get()
            except asyncio.exceptions.TimeoutError:
                if cm.expired:
                    message = ''
            await submit_message(writer, message)
            if message:
                logger.info(f'Sending "{message}"')
                watchdog_queue.put_nowait('Message sent')
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)


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


async def watch_for_connection(watchdog_queue):
    while True:
        message = await watchdog_queue.get()
        if 'timeout' in message:
            watchdog_logger.info(message)
            raise ConnectionError
        else:
            watchdog_logger.info(f'Connection is alive. Source: {message}')


async def main():
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
    watchdog_queue = asyncio.Queue()

    await restore_messages(config['history_file'], messages_queue)

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
            tg.start_soon(save_messages, config['history_file'], history_queue)
            tg.start_soon(
                handle_connection,
                config,
                messages_queue,
                sending_queue,
                history_queue,
                status_updates_queue,
                watchdog_queue
            )
    except InvalidToken:
        await gui.show_token_error()
    finally:
        tg.cancel_scope.cancel()


if __name__ == '__main__':
    with suppress(KeyboardInterrupt, gui.TkAppClosed):
        anyio.run(main)
