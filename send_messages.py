import argparse
import asyncio

from aioconsole import ainput
from environs import Env


async def send_messages(host, port, hash):
    if not hash:
        return
    reader, writer = await asyncio.open_connection(host, port)
    message = await reader.readline()
    print(message.decode())
    writer.write(f'{hash}\n'.encode())
    await writer.drain()
    message = await reader.readline()
    print(message.decode())
    while True:
        message = await ainput('Type a message: ')
        writer.write(f'{message}\n\n'.encode())
        await writer.drain()


def main():
    env = Env()
    env.read_env()

    parser = argparse.ArgumentParser(description='Send messages to chat')
    parser.add_argument('--host', '-s', action='store', help='Host')
    parser.add_argument('--port', '-p', type=int, action='store', help='Port')
    parser.add_argument('--hash', action='store', help='Chat hash')
    args = parser.parse_args()

    minechat_config = {
        'host': args.host if args.host else env('HOST', default='minechat.dvmn.org'),
        'port': args.port if args.port else env.int('WRITING_PORT', default=5050),
        'hash': args.hash if args.hash else env('CHAT_HASH')
    }

    asyncio.run(send_messages(**minechat_config))


if __name__ == '__main__':
    main()
