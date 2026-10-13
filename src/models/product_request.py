from dataclasses import dataclass


@dataclass(frozen=True)
class ProductRequest:
    user_id: int
    chat_id: int
    message_id: int
    url: str
    received_at: str
