import argparse
import asyncio
import json
import logging

import aiofiles
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
    await write_to_chat(f'{token}\n')
    return await receive_credentials(reader)


async def sign_up(reader, writer, nickname, send_blank=False):
    if send_blank:
        await write_to_chat('\n')
    nickname_query = await reader.readline()
    logger.info(nickname_query.decode().strip())
    logger.info(f'Sending "{nickname}"')
    await write_to_chat(f'{nickname}\n')
    return await receive_credentials(reader)


async def submit_message(writer, message):
    message = message.replace('\n', ' ')
    await write_to_chat(f'{message}\n\n')


async def write_to_chat(writer, message):
    writer.write(message.encode())
    await writer.drain()


async def send_message(message, host, port, token, nickname):
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

    await submit_message(writer, message)
    writer.close()


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
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'port': args.port if args.port else env.int('WRITING_PORT', default=5050),
        'token': args.token if args.token else env('CHAT_TOKEN', default=''),
        'nickname': args.nickname if args.nickname else env('CHAT_NICKNAME', default='')
    }

    asyncio.run(send_message(**minechat_config))


if __name__ == '__main__':
    main()
