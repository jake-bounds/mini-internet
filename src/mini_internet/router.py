from dataclasses import dataclass
import socket

from mini_internet.config import ALL_CONFIGS
from mini_internet.packet import Packet


@dataclass
class Args:
    id: str


def start_router(host: str, port: int, next_hop_table: dict[str, str]):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((host, port))

        while True:
            data, addr = sock.recvfrom(4096)
            packet = Packet.from_bytes(data)

            packet.hop_limit -= 1
            if packet.hop_limit == 0:
                continue

            dest_cfg = ALL_CONFIGS[packet.dest_addr]
            sock.sendto(packet.to_bytes(), (host, dest_cfg.host_port))
