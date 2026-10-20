from dataclasses import dataclass


@dataclass
class HostConfig:
    addr: str
    router_addr: str
    host_port: int = 0


@dataclass
class RouterConfig:
    addr: str
    next_hop: dict[str, str]  # Destination host addr -> next router addr
    host_port: int = 0


Addressable = HostConfig | RouterConfig

BASE_PORT = 31215

HOST_CONFIGS = [HostConfig("h1", "r1"), HostConfig("h2", "r2")]

ROUTER_CONFIGS = [
    RouterConfig("r1", {"r1": "r1", "r2": "h3"}),
    RouterConfig("r2", {"r1": "h3", "r2": "r2"}),
    RouterConfig("r3", {"r1": "h1", "r2": "h2"}),
]

for i, cfg in enumerate(HOST_CONFIGS + ROUTER_CONFIGS):
    cfg.host_port = BASE_PORT + i

ALL_CONFIGS = {cfg.addr: cfg for cfg in HOST_CONFIGS + ROUTER_CONFIGS}
HOST_CONFIGS = {cfg.addr: cfg for cfg in HOST_CONFIGS}
ROUTER_CONFIGS = {cfg.addr: cfg for cfg in ROUTER_CONFIGS}
