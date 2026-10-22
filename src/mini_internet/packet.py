from base64 import b64decode, b64encode
from dataclasses import dataclass
import dataclasses
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
        return json.dumps(
            {**self.__dict__, "payload": b64encode(self.payload).decode()}
        ).encode()

    @classmethod
    def from_bytes(cls, data: bytes):
        j = json.loads(data.decode())
        j["payload"] = b64decode(j["payload"], validate=True)
        return cls(**j)

    def __post_init__(self):
        # Type validation
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, field.type):
                raise TypeError(
                    f"Field '{field.name}' must be of type {field.type}, "
                    f"got {type(value).__name__} instead."
                )
