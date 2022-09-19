import argparse
import asyncio
import logging

from aioconsole import ainput
from environs import Env

logger = logging.getLogger(__name__)


async def sign_in(reader, writer, token):
    logger.info(f'Sending "{token}"')
    writer.write(f'{token}\n'.encode())
    await writer.drain()
    credentials_response = await reader.readline()
    credentials_response = credentials_response.decode().strip()
    logger.info(credentials_response)
    return credentials_response


async def sign_up(reader, writer, nickname):
    nickname_query = await reader.readline()
    logger.info(nickname_query.decode().strip())
    logger.info(f'Sending "{nickname}"')
    writer.write(f'{nickname}\n'.encode())
    await writer.drain()
    credentials_response = await reader.readline()
    credentials_response = credentials_response.decode().strip()
    logger.info(credentials_response)
    return credentials_response


async def send_messages(host, port, token, nickname):
    reader, writer = await asyncio.open_connection(host, port)
    greeting_query = await reader.readline()
    logger.info(greeting_query.decode().strip())

    if token:
        credentials_response = await sign_in(reader, writer, token)
        if credentials_response == 'null':
            credentials_response = await sign_up(reader, writer, nickname)
    else:
        writer.write('\n'.encode())
        await writer.drain()
        credentials_response = await sign_up(reader, writer, nickname)

    while True:
        message = await ainput('Type a message: ')
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()


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
