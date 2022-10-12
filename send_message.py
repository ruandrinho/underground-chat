import argparse
import asyncio
import json
import logging

import aiofiles
from environs import Env

from minechat import get_minechat_connection

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


async def authorize_and_send_message(message, host, port, token, nickname):
    async with get_minechat_connection(host, port) as (reader, writer):
        greeting_query = await reader.readline()
        logger.info(greeting_query.decode().strip())

        if token:
            credentials = await sign_in(reader, writer, token)
            if not credentials:
                logger.warning('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
                credentials = await sign_up(reader, writer, nickname)
        else:
            credentials = await sign_up(reader, writer, nickname, send_blank=True)
        await save_token(credentials['nickname'], credentials['account_hash'])

        await submit_message(writer, message)


def main():

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Send messages to chat')
    parser.add_argument('message', nargs='+', help='Message for chat')
    parser.add_argument('--host', '-s', help='Host')
    parser.add_argument('--port', '-p', type=int, help='Port')
    parser.add_argument('--token', '-t', help='Chat token')
    parser.add_argument('--nickname', '-n', help='Chat nickname')
    args = parser.parse_args()

    minechat_config = {
        'message': args.message[0],
        'host': args.host or env('HOST', default='minechat.dvmn.org'),
        'port': args.port or env.int('WRITING_PORT', default=5050),
        'token': args.token or env('CHAT_TOKEN', default=''),
        'nickname': args.nickname or env('CHAT_NICKNAME', default='')
    }

    asyncio.run(authorize_and_send_message(**minechat_config))


if __name__ == '__main__':
    main()
