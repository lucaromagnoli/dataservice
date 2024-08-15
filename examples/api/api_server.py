from faker import Faker
from fastapi import FastAPI

# import all you need from fastapi-pagination
from fastapi_pagination import Page, add_pagination, paginate

from examples.api.models import User

app = FastAPI()
fake = Faker()

users = [  # create some data
    User(name=fake.first_name(), surname=fake.last_name()) for _ in range(1000)
]


@app.get("/users")
async def get_users() -> Page[User]:  # use Page[UserOut] as return type annotation
    return paginate(users)  # use paginate function to paginate your data


add_pagination(app)  # important! add pagination to your app
