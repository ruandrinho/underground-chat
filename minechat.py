import asyncio
import json
import logging
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import anyio
from async_timeout import timeout

import gui_main

logger = logging.getLogger('minechat')
watchdog_logger = logging.getLogger('minechat_watchdog')


class InvalidToken(Exception):
    pass


@asynccontextmanager
async def get_connection(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def handle_connection(config, messages_queue, sending_queue, history_queue, status_updates_queue, watchdog_queue):
    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(
                read_messages,
                config,
                messages_queue,
                history_queue,
                status_updates_queue,
                watchdog_queue
            )
            tg.start_soon(
                send_messages,
                config,
                sending_queue,
                messages_queue,
                status_updates_queue,
                watchdog_queue
            )
            tg.start_soon(ping_pong, config, status_updates_queue, watchdog_queue)
            tg.start_soon(watch_for_connection, watchdog_queue)
    except (ConnectionError, socket.gaierror, anyio.ExceptionGroup) as exception:
        tg.cancel_scope.cancel()
        if exception.__class__.__name__ != 'ConnectionError':
            logger.info('Reconnecting with timeout')
            await anyio.sleep(config['big_reconnect_timeout'])
        else:
            logger.info('Reconnecting')
        await handle_connection(
            config, messages_queue, sending_queue, history_queue, status_updates_queue, watchdog_queue
        )


async def ping_pong(config, status_updates_queue, watchdog_queue):
    async with get_connection(config['host'], config['writing_port']) as (reader, writer):
        while True:
            await submit_message(writer, '')
            try:
                async with timeout(config['small_reconnect_timeout']) as cm:
                    await reader.readline()
                    status_updates_queue.put_nowait(gui_main.SendingConnectionStateChanged.ESTABLISHED)
            except asyncio.exceptions.TimeoutError:
                if cm.expired:
                    watchdog_queue.put_nowait('Small timeout is elapsed')


async def read_messages(config, messages_queue, history_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui_main.ReadConnectionStateChanged.INITIATED)
    async with get_connection(config['host'], config['reading_port']) as (reader, writer):
        while not reader.at_eof():
            message = await reader.readline()
            message = message.decode().strip()
            messages_queue.put_nowait(message)
            history_queue.put_nowait(message)
            watchdog_queue.put_nowait('New message in chat')
            status_updates_queue.put_nowait(gui_main.ReadConnectionStateChanged.ESTABLISHED)


async def restore_messages(filepath, messages_queue):
    if not Path(filepath).exists():
        return
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as chatfile:
        history = await chatfile.read()
        messages_queue.put_nowait(history)


async def save_messages(filepath, history_queue):
    async with aiofiles.open(filepath, 'a', encoding='utf-8') as chatfile:
        while True:
            message = await history_queue.get()
            await chatfile.write(f'{message}\n')


async def send_messages(config, sending_queue, messages_queue, status_updates_queue, watchdog_queue):
    status_updates_queue.put_nowait(gui_main.SendingConnectionStateChanged.INITIATED)
    async with get_connection(config['host'], config['writing_port']) as (reader, writer):
        greeting_query = await reader.readline()
        logger.info(greeting_query.decode().strip())

        credentials = await sign_in(reader, writer, config['token'])
        if not credentials:
            raise InvalidToken
        messages_queue.put_nowait(f'Выполнена авторизация. Пользователь {credentials["nickname"]}')
        event = gui_main.NicknameReceived(credentials['nickname'])
        status_updates_queue.put_nowait(event)

        while True:
            message = await sending_queue.get()
            await submit_message(writer, message)
            logger.info(f'Sending "{message}"')
            watchdog_queue.put_nowait('Message sent')
            status_updates_queue.put_nowait(gui_main.SendingConnectionStateChanged.ESTABLISHED)


async def watch_for_connection(watchdog_queue):
    while True:
        message = await watchdog_queue.get()
        if 'timeout' in message:
            watchdog_logger.info(message)
            raise ConnectionError
        else:
            watchdog_logger.info(f'Connection is alive. Source: {message}')


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
    nickname_query = await reader.readline()
    logger.info(nickname_query.decode().strip())
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
