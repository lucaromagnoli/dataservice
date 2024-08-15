"""Fictional API server for demonstration purposes."""

from faker import Faker
from fastapi import FastAPI
from fastapi_pagination import Page, add_pagination, paginate

from examples.api.models import User

app = FastAPI()
fake = Faker()

users = [  # create some data
    User(name=fake.first_name(), surname=fake.last_name()) for _ in range(1000)
]


@app.get("/users")
async def get_users() -> Page[User]:
    return paginate(users)


add_pagination(app)
