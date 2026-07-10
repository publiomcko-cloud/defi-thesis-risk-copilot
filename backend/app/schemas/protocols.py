from pydantic import BaseModel


class Protocol(BaseModel):
    id: str
    name: str
    category: str
    supported_in_mvp: bool
    description: str


class ProtocolListResponse(BaseModel):
    protocols: list[Protocol]
