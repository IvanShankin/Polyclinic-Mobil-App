import asyncio


def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()