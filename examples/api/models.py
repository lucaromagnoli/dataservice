from pydantic import BaseModel, Field


class User(BaseModel):  # define your model
    name: str = Field(..., examples=["Steve"])
    surname: str = Field(..., examples=["Rogers"])
