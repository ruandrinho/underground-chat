import asyncio
import gui
import time


async def generate_msgs(queue):
    while True:
        queue.put_nowait(round(time.time()))
        await asyncio.sleep(1)


async def main():
    loop = asyncio.get_event_loop()

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    loop.run_until_complete(
        await asyncio.gather(
            gui.draw(messages_queue, sending_queue, status_updates_queue),
            generate_msgs(messages_queue)
    ))


if __name__ == '__main__':
    asyncio.run(main())
