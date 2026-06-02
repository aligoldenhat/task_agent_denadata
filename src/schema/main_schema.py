from pydantic import BaseModel


class RecieveSchema(BaseModel):
    conversation_id: str | None = None
    message: str


class ResponseSchema(BaseModel):
    conversation_id: str
    answer: str
