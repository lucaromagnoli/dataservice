from logging import getLogger
from pprint import pprint

from dataservice import (
    DataService,
    PlaywrightClient,
    PlaywrightPage,
    Request,
    Response,
    setup_logging,
)

logger = getLogger("interceptor_button")
setup_logging("interceptor_button")


async def press_button(page: PlaywrightPage):
    has_posts = True
    while has_posts:
        await page.get_by_role("button").click()
        await page.wait_for_timeout(1000)
        no_more_posts = page.get_by_text("No more posts")
        if await no_more_posts.is_visible():
            has_posts = False


def parse_intercepted(response: Response):
    for url in response.data:
        for item in response.data[url]:
            yield {"url": url, **item}


def main():
    client = PlaywrightClient(actions=press_button, intercept_url="posts")
    start_requests = [
        Request(
            url="https://lucaromagnoli.github.io/ds-mock-spa/#/load-more",
            callback=parse_intercepted,
            client=client,
        )
    ]
    service = DataService(start_requests)
    data = tuple(service)
    pprint(data)


if __name__ == "__main__":
    main()
