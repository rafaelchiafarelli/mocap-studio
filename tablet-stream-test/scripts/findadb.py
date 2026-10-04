#!/usr/bin/env python3
"""Find a tablet's Wireless debugging port (random, changes on every reboot/toggle) by scanning it.

usage: findadb.py <ip> [--from 30000] [--to 46000]   -> prints the open port(s)
"""
import argparse
import asyncio


async def scan(ip, lo, hi):
    sem = asyncio.Semaphore(800)

    async def probe(port):
        async with sem:
            try:
                _, w = await asyncio.wait_for(asyncio.open_connection(ip, port), 0.6)
                w.close()
                return port
            except Exception:
                return None

    return [p for p in await asyncio.gather(*(probe(p) for p in range(lo, hi))) if p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ip")
    ap.add_argument("--from", dest="lo", type=int, default=30000)
    ap.add_argument("--to", dest="hi", type=int, default=46000)
    args = ap.parse_args()
    print(" ".join(str(p) for p in asyncio.run(scan(args.ip, args.lo, args.hi))))


if __name__ == "__main__":
    main()
