# coding=utf-8
import asyncio
import threading


class Tasks:
    loop = asyncio.new_event_loop()

    @classmethod
    def _run(cls):
        asyncio.set_event_loop(cls.loop)

        try:
            cls.loop.run_forever()
        finally:
            cls.loop.close()

    @classmethod
    def do(cls, func, *args, **kwargs):
        handle = cls.loop.call_soon_threadsafe(lambda: func(*args, **kwargs))
        cls.loop._write_to_self()

        return handle

    @classmethod
    def later(cls, func, *args, after=None, **kwargs):
        handle = cls.loop.call_later(after, lambda: func(*args, **kwargs))
        cls.loop._write_to_self()

        return handle

    @classmethod
    def periodic(cls, func, *args, interval=None, **kwargs):
        async def f():
            while True:
                await asyncio.sleep(interval)
                func(*args, **kwargs)

        handle = cls.loop.create_task(f())
        cls.loop._write_to_self()

        return handle


threading.Thread(name="tasks", target=Tasks._run, daemon=True).start()
