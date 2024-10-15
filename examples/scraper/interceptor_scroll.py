from logging import getLogger
from pathlib import Path
from pprint import pprint

from dataservice import (
    DataService,
    PlaywrightClient,
    PlaywrightPage,
    Request,
    Response,
    setup_logging,
)

logger = getLogger("interceptor_scroll")
setup_logging("interceptor_scroll")


async def scroll_to_bottom(page: PlaywrightPage):
    script_path = Path(__file__).parent / "scroll_to_bottom.js"
    with open(script_path) as f:
        script = f.read()
    await page.evaluate(script)


def parse_intercepted(response: Response):
    for url in response.data:
        for item in response.data[url]:
            yield {"url": url, **item}


def main():
    client = PlaywrightClient(actions=scroll_to_bottom, intercept_url="posts")
    start_requests = [
        Request(
            url="https://lucaromagnoli.github.io/ds-mock-spa/#/infinite-scroll",
            callback=parse_intercepted,
            client=client,
        )
    ]
    service = DataService(start_requests)
    data = tuple(service)
    pprint(data)


if __name__ == "__main__":
    main()
