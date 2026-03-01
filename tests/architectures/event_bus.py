import asyncio
import time
import random

class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event, fn):
        self.subscribers.setdefault(event, []).append(fn)
        print(self.subscribers)

    def publish_sync(self, event, data):
        handlers = self.subscribers.get(event, [])

        for fn in handlers:
            fn(data)

    async def publish_async(self, event, data):
        handlers = self.subscribers.get(event, [])
        if not handlers:
            return
        await asyncio.gather(*(fn(data) for fn in handlers))

# Create the bus
bus = EventBus()

async def macro_analyst(data):
    print(f"Agent A received data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    print(f"Agent A is processing data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    print(f"Agent A is done processing data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))

async def equity_analyst(data):
    print(f"Agent B received data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    print(f"Agent B is processing data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    print(f"Agent B is done processing data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))

async def fixed_income_analyst(data):
    print(f"Agent C received data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    print(f"Agent C is done processing data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    print(f"Agent C is done processing data: {data}")
    await asyncio.sleep(random.uniform(0.2, 1.0))

bus.subscribe("macro_data_update", macro_analyst)
bus.subscribe("equity_data_update", equity_analyst)
bus.subscribe("fixed_income_data_update", fixed_income_analyst)

async def main():
    await asyncio.gather(
        bus.publish_async("macro_data_update", "New jobs report released"),
        bus.publish_async("equity_data_update", "New earnings report released"),
        bus.publish_async("fixed_income_data_update", "New bond issuance report released"),
    )

asyncio.run(main())
