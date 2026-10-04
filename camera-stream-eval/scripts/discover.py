#!/usr/bin/env python3
"""Find every tablet running the stream app on the local /24 (asks http://<ip>:8080/stats).

usage: discover.py [--subnet 192.168.7] [--port 8080]
"""
import argparse
import concurrent.futures
import json
import socket
import urllib.request


def local_subnet():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # no packet is sent; just picks the outgoing interface
        return s.getsockname()[0].rsplit(".", 1)[0]
    finally:
        s.close()


def probe(ip, port):
    try:
        with urllib.request.urlopen(f"http://{ip}:{port}/stats", timeout=0.8) as r:
            j = json.loads(r.read())
        return ip, j
    except Exception:
        return ip, None


def discover(subnet=None, port=8080):
    subnet = subnet or local_subnet()
    with concurrent.futures.ThreadPoolExecutor(64) as ex:
        found = [(ip, j) for ip, j in ex.map(lambda n: probe(f"{subnet}.{n}", port), range(1, 255)) if j]
    return sorted(found, key=lambda x: int(x[0].rsplit(".", 1)[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subnet", help="first three octets, default: this PC's subnet")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    found = discover(args.subnet, args.port)
    for ip, j in found:
        print(f"{ip:15s} {j.get('device', '?'):22s} {j.get('encoded_fps', 0):5.1f} fps {j.get('mbps', 0):5.1f} Mbps  "
              f"{j.get('config', '')}")
    if not found:
        print("no tablets found")


if __name__ == "__main__":
    main()
