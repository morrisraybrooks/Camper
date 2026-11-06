"""Find the Furrion stereo over BLE, do the ES Control handshake, print replies. Sends no key commands."""
import asyncio
from bleak import BleakScanner, BleakClient

SERVICE = "0000a032-0000-1000-8000-00805f9b34fb"
WRITE = "0000a040-0000-1000-8000-00805f9b34fb"
ADDRESS = "00:13:04:02:45:EE"
NOTIFY = "0000a042-0000-1000-8000-00805f9b34fb"


async def main():
    target = ADDRESS
    print("found", target)
    if not target:
        return

    replies = []

    async with BleakClient(target, timeout=20) as client:
        print("connected", client.address)
        for s in client.services:
            print(" service", s.uuid, [(c.uuid[4:8], c.properties) for c in s.characteristics])

        async def on_notify(_, data: bytearray):
            text = data.decode(errors="replace")
            print("  <<", repr(text))
            replies.append(text)
            if text.startswith("MCU+CHK"):
                # The app echoes the challenge back with SLV, dropping the trailing '&'.
                await client.write_gatt_char(WRITE, text.replace("MCU", "SLV")[:-1].encode())

        await client.start_notify(NOTIFY, on_notify)
        await client.write_gatt_char(WRITE, b"SLV+CHK+F01&")
        print("  >> 'SLV+CHK+F01&'")
        await asyncio.sleep(10)
    print(f"done, {len(replies)} replies")


asyncio.run(main())
