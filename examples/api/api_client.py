import logging

from dataservice import (
    DataService,
    HttpXClient,
    Request,
    Response,
    ServiceConfig,
    setup_logging,
)
from examples.api.models import User

logger = logging.getLogger("api_client")

setup_logging("api_client")


def parse_users(response: Response):
    users = response.data["items"]
    for user in users:
        yield User(**user)


def paginate(response: Response):
    pages = response.data["pages"]
    yield from parse_users(response)
    for p in range(2, pages + 1):
        yield Request(
            url=response.request.url,
            callback=parse_users,
            client=response.request.client,
            params={"page": p},
            content_type="json",
        )


def main():
    httpx_client = HttpXClient()
    start_requests = [
        Request(
            url="http://127.0.0.1:8000/users",
            callback=paginate,
            client=httpx_client,
            content_type="json",
        )
    ]
    data_service = DataService(
        start_requests, config=ServiceConfig(**{"limiter": {"max_rate": 10}})
    )
    data = tuple(data_service)
    for item in data:
        logger.info(item)


if __name__ == "__main__":
    main()
