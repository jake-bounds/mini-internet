from dataclasses import dataclass
import json


@dataclass
class Packet:
    source_addr: str
    dest_addr: str
    msg_id: str
    hop_limit: int
    msg_type: str
    payload: bytes

    def to_bytes(self):
        return json.dumps(self.__dict__).encode()

    @classmethod
    def from_bytes(cls, data: bytes):
        return cls(**json.loads(data.decode()))
