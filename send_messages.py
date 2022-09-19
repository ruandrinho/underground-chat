import argparse
import asyncio
import json
import logging

import aiofiles
from aioconsole import ainput
from environs import Env

logger = logging.getLogger(__name__)


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
    writer.write(f'{token}\n'.encode())
    await writer.drain()
    return await receive_credentials(reader)


async def sign_up(reader, writer, nickname, send_blank=False):
    if send_blank:
        writer.write('\n'.encode())
        await writer.drain()
    nickname_query = await reader.readline()
    logger.info(nickname_query.decode().strip())
    logger.info(f'Sending "{nickname}"')
    writer.write(f'{nickname}\n'.encode())
    await writer.drain()
    return await receive_credentials(reader)


async def submit_message(writer, message):
    writer.write(f'{message}\n\n'.encode())
    await writer.drain()


async def send_messages(host, port, token, nickname):
    reader, writer = await asyncio.open_connection(host, port)
    greeting_query = await reader.readline()
    logger.info(greeting_query.decode().strip())

    if token:
        credentials = await sign_in(reader, writer, token)
        if credentials is None:
            logger.warning('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
            credentials = await sign_up(reader, writer, nickname)
    else:
        credentials = await sign_up(reader, writer, nickname, send_blank=True)
    await save_token(credentials['nickname'], credentials['account_hash'])

    while True:
        message = await ainput('Type a message: ')
        await submit_message(writer, message)


def main():

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Send messages to chat')
    parser.add_argument('--host', '-s', action='store', help='Host')
    parser.add_argument('--port', '-p', type=int, action='store', help='Port')
    parser.add_argument('--token', '-t', action='store', help='Chat token')
    parser.add_argument('--nickname', '-n', action='store', help='Chat nickname')
    args = parser.parse_args()

    minechat_config = {
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'port': args.port if args.port else env.int('WRITING_PORT', default=5050),
        'token': args.token if args.token else env('CHAT_TOKEN', default=''),
        'nickname': args.nickname if args.nickname else env('CHAT_NICKNAME', default='')
    }

    asyncio.run(send_messages(**minechat_config))


if __name__ == '__main__':
    main()
