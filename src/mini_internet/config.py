from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass
class HostConfig:
    addr: str
    router_addr: str
    host_port: int
    delays: dict[str, float]
    loss: dict[str, float]


@dataclass
class RouterConfig:
    addr: str
    neighbor_addrs: list[str]
    next_hop: dict[str, str]  # Destination host addr -> next router addr
    host_port: int
    delays: dict[str, float]
    loss: dict[str, float]


Addressable = HostConfig | RouterConfig

ALL_CONFIGS: dict[str, Addressable] = {}

HOST_CONFIGS: dict[str, HostConfig] = {}

ROUTER_CONFIGS: dict[str, RouterConfig] = {}


def fetch_configs(topology_path: Path, nc_path: Path):
    ALL_CONFIGS.clear()
    HOST_CONFIGS.clear()
    ROUTER_CONFIGS.clear()

    if not topology_path.exists():
        raise FileNotFoundError(f"Config file {topology_path} does not exist.")

    if not nc_path.exists():
        raise FileNotFoundError(f"Config file {nc_path} does not exist.")

    with open(topology_path, "rb") as f:
        top_cfg = tomllib.load(f)

    with open(nc_path, "rb") as f:
        nc_cfg = tomllib.load(f)

    for addr, v in top_cfg["hosts"].items():
        hcfg = HostConfig(addr, v["router_addr"], v["port"], {}, {})
        HOST_CONFIGS[addr] = hcfg

    for addr, v in top_cfg["routers"].items():
        rcfg = RouterConfig(addr, v["neighbors"], v["next_hop"], v["port"], {}, {})
        ROUTER_CONFIGS[addr] = rcfg

    for src, d in nc_cfg.get("links", {}).items():
        for dest, vals in d.items():
            if (
                src not in HOST_CONFIGS
                and src not in ROUTER_CONFIGS
                or dest not in HOST_CONFIGS
                and dest not in ROUTER_CONFIGS
            ):
                raise ValueError(
                    f"Conditions defined for non-existent source or destination {src}, {dest}."
                )

            if (
                src in HOST_CONFIGS
                and dest != HOST_CONFIGS[src].router_addr
                or src in ROUTER_CONFIGS
                and dest not in ROUTER_CONFIGS[src].neighbor_addrs
            ):
                raise ValueError(
                    f"Conditions defined for {src} -> {dest} but no such link exists."
                )
            if src in HOST_CONFIGS:
                HOST_CONFIGS[src].loss[dest] = vals.get("loss", 0)
                HOST_CONFIGS[src].delays[dest] = vals.get("delay_ms", 0)
            else:
                ROUTER_CONFIGS[src].loss[dest] = vals.get("loss", 0)
                ROUTER_CONFIGS[src].delays[dest] = vals.get("delay_ms", 0)

    ALL_CONFIGS.update(HOST_CONFIGS | ROUTER_CONFIGS)

    if not HOST_CONFIGS.keys().isdisjoint(ROUTER_CONFIGS.keys()):
        raise ValueError("A host and router share an address.")

    for h in HOST_CONFIGS.values():
        if h.router_addr not in ROUTER_CONFIGS:
            raise ValueError(
                f"{h.addr} has router {h.router_addr} but no such router is configured."
            )

    for r in ROUTER_CONFIGS.values():
        for d in r.next_hop.values():
            if d not in r.neighbor_addrs:
                raise ValueError(
                    f"{r.addr} has next hop destination of {d} not in neighbors."
                )
