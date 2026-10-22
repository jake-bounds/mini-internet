import argparse
import asyncio
from dataclasses import dataclass
import os
from pathlib import Path
from random import Random
import secrets
import time

from mini_internet.config import HOST_CONFIGS, ROUTER_CONFIGS, fetch_configs
from mini_internet.packet import Packet

PROBE_TIMEOUT = 5
HOP_LIMIT = 5

random = Random()


@dataclass
class Args:
    addr: str
    topology: Path
    network_conditions: Path
    seed: int


@dataclass
class PendingProbe:
    msg_id: str
    timer: asyncio.TimerHandle
    payload: bytes
    send_time: float


class Host(asyncio.DatagramProtocol):
    addr: str
    loop: asyncio.AbstractEventLoop
    transport: asyncio.DatagramTransport
    pending_probes: dict[str, PendingProbe]

    def __init__(self, addr: str, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self.addr = addr
        self.loop = loop
        self.pending_probes = {}

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        """Called when some datagram is received."""
        try:
            packet = Packet.from_bytes(data)
        except (ValueError, KeyError, TypeError) as e:
            print("Malformed packet:", e)
            return

        if packet.dest_addr != self.addr:
            print(f"Received packet directed to {packet.dest_addr}.")
            return

        if packet.msg_type == "echo":
            if packet.msg_id in self.pending_probes:
                self.recv_probe(packet.msg_id, packet.payload)
            else:
                print(
                    f"Received echo for a probe that wasn't sent by us ({packet.msg_id})."
                )
            return

        if packet.msg_type == "probe":
            print(f"Received probe {packet.msg_id}. Echoing.")
            echo = Packet(
                self.addr,
                packet.source_addr,
                packet.msg_id,
                HOP_LIMIT,
                "echo",
                packet.payload,
            )
            self.send(echo)
            return

        try:
            msg = packet.payload.decode()
            print(f"RECV {packet.msg_id}: {msg}")
        except UnicodeDecodeError:
            print(f"RECV {packet.msg_id}: <Cannot be decoded>")

    def send(self, packet: Packet):
        router_port = ROUTER_CONFIGS[HOST_CONFIGS[self.addr].router_addr].host_port
        next_hop = ("127.0.0.1", router_port)

        payload = packet.to_bytes()

        # Link loss
        loss_prob = HOST_CONFIGS[self.addr].loss.get(
            HOST_CONFIGS[self.addr].router_addr, 0
        )
        if random.random() < loss_prob:
            print(f"Randomly dropping packet {packet.msg_id}")
            return

        # Link delay
        delay = HOST_CONFIGS[self.addr].delays.get(
            HOST_CONFIGS[self.addr].router_addr, 0
        )
        if delay == 0:
            self.transport.sendto(payload, next_hop)
        else:
            self.loop.call_later(delay / 1000, self.transport.sendto, payload, next_hop)

    def send_probe(self, dest_addr: str, payload: bytes):
        msg_id = secrets.token_hex(2)
        packet = Packet(self.addr, dest_addr, msg_id, HOP_LIMIT, "probe", payload)
        start_time = time.monotonic()
        timer = self.loop.call_later(
            PROBE_TIMEOUT, self.norecv_probe, packet.msg_id, PROBE_TIMEOUT
        )
        self.pending_probes[packet.msg_id] = PendingProbe(
            packet.msg_id, timer, payload, start_time
        )
        print(f"Sending probe {msg_id} to {dest_addr}.")
        self.send(packet)

    def recv_probe(self, msg_id: str, payload: bytes):
        time_recv = time.monotonic()
        dt = time_recv - self.pending_probes[msg_id].send_time
        self.pending_probes[msg_id].timer.cancel()

        if payload == self.pending_probes[msg_id].payload:
            print(f"Response received for probe {msg_id} in {dt} seconds.")
        else:
            print(
                f"Response with bad payload received for probe {msg_id} in {dt} seconds."
            )

        self.pending_probes.pop(msg_id)

    def norecv_probe(self, msg_id: str, timeout: int):
        self.pending_probes.pop(msg_id)
        print(f"No response received for probe {msg_id} in {timeout} seconds.")


def parse_args() -> Args:
    parser = argparse.ArgumentParser()
    parser.add_argument("--addr", required=True)
    parser.add_argument("--topology", type=Path, required=True)
    parser.add_argument("--network-conditions", type=Path, required=True)
    parser.add_argument(
        "--seed", type=int, default=int(os.environ.get("SEED", time.time()))
    )

    args = parser.parse_args()
    return Args(**args.__dict__)


async def start():
    args = parse_args()
    seed = f"{args.seed}:{args.addr}"
    print("Using seed", seed)
    random.seed(seed)
    fetch_configs(args.topology, args.network_conditions)

    cfg = HOST_CONFIGS[args.addr]
    loop = asyncio.get_running_loop()
    host = Host(cfg.addr, loop)
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: host, local_addr=("127.0.0.1", cfg.host_port)
    )

    print("To send a probe, type <dest_addr>:<msg> and press enter.")

    try:

        while True:
            try:
                cin = await asyncio.to_thread(input)
            except EOFError:
                break

            if cin.find(":") == -1:
                print(
                    "To send a probe, type <dest_addr>:<msg> separated by a colon and press enter."
                )
                continue

            dest_addr, msg = cin.split(":", 1)
            if dest_addr not in HOST_CONFIGS:
                pass

                # commented for acceptance criteria
                # print(f"Unknown host {dest_addr}")
                # continue

            protocol.send_probe(dest_addr, msg.encode())
    finally:
        transport.close()


def main():
    asyncio.run(start())


if __name__ == "__main__":
    main()
