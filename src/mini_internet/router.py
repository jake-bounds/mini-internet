import argparse
from dataclasses import dataclass
import os
from pathlib import Path
from random import Random
import secrets
import socket
import threading
import time

from mini_internet.config import (
    ALL_CONFIGS,
    HOST_CONFIGS,
    ROUTER_CONFIGS,
    fetch_configs,
)
from mini_internet.packet import Packet

random = Random()

run_id = os.environ.get("RUN_ID") or "norunid"


@dataclass
class Args:
    addr: str
    topology: Path
    network_conditions: Path
    seed: int


@dataclass
class Router:
    addr: str
    host: str
    port: int
    next_hop_table: dict[str, str]
    sock: socket.socket | None = None

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

        return self

    def __exit__(self, *args):
        if self.sock:
            self.sock.__exit__(*args)

    def start(self):
        if not self.sock:
            raise RuntimeError("Router.start() must be ran in a ContextManager.")

        while True:
            data, _ = self.sock.recvfrom(2048)

            if len(data) > 1200:
                print(
                    f"{run_id} | {self.addr} | {time.time()} | receive,drop (too large)"
                )
                continue

            try:
                packet = Packet.from_bytes(data)
            except ValueError, KeyError, TypeError:
                print(
                    f"{run_id} | {self.addr} | {time.time()} | receive,drop (failed to decode)"
                )
                continue

            if packet.dest_addr not in self.next_hop_table:
                print(
                    f"{run_id} | {self.addr} | {time.time()} | {packet.msg_id} | {packet.msg_type} | {packet.source_addr} | {packet.dest_addr} | null | {packet.hop_limit} | drop (no known next hop)"
                )
                continue
            next_hop_addr = self.next_hop_table[packet.dest_addr]
            print(
                f"{run_id} | {self.addr} | {time.time()} | {packet.msg_id} | {packet.msg_type} | {packet.source_addr} | {packet.dest_addr} | {next_hop_addr} | {packet.hop_limit} | receive"
            )

            if packet.dest_addr not in HOST_CONFIGS:
                print(
                    f"{run_id} | {self.addr} | {time.time()} | {packet.msg_id} | {packet.msg_type} | {packet.source_addr} | {packet.dest_addr} | {next_hop_addr} | {packet.hop_limit} | drop (unknown destination)"
                )
                continue

            packet.hop_limit -= 1
            if packet.hop_limit <= 0:
                print(
                    f"{run_id} | {self.addr} | {time.time()} | {packet.msg_id} | {packet.msg_type} | {packet.source_addr} | {packet.dest_addr} | {next_hop_addr} | {packet.hop_limit} | drop (hop limit)"
                )
                continue

            # Link loss
            loss_prob = ROUTER_CONFIGS[self.addr].loss.get(next_hop_addr, 0)
            if random.random() < loss_prob:
                print(
                    f"{run_id} | {self.addr} | {time.time()} | {packet.msg_id} | {packet.msg_type} | {packet.source_addr} | {packet.dest_addr} | {next_hop_addr} | {packet.hop_limit} | drop ({"random link drop" if loss_prob < 1 else "injected loss"})"
                )
                continue

            # Link delay
            dest_cfg = ALL_CONFIGS[next_hop_addr]
            delay = ROUTER_CONFIGS[self.addr].delays.get(next_hop_addr, 0)
            print(
                f"{run_id} | {self.addr} | {time.time()} | {packet.msg_id} | {packet.msg_type} | {packet.source_addr} | {packet.dest_addr} | {next_hop_addr} | {packet.hop_limit} | forward"
            )
            if delay == 0:
                self.sock.sendto(packet.to_bytes(), (self.host, dest_cfg.host_port))
            else:
                threading.Timer(
                    delay / 1000,
                    self.sock.sendto,
                    args=(packet.to_bytes(), (self.host, dest_cfg.host_port)),
                ).start()


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


def main():
    args = parse_args()
    seed = f"{args.seed}:{args.addr}"
    print("Using seed", seed)
    random.seed(seed)
    fetch_configs(args.topology, args.network_conditions)
    router_cfg = ROUTER_CONFIGS[args.addr]
    with Router(
        router_cfg.addr, "127.0.0.1", router_cfg.host_port, router_cfg.next_hop
    ) as router:
        router.start()


if __name__ == "__main__":
    main()
