from dataservice.client import Client
from dataservice.messages import Request, Response


class ToyClient(Client):
    async def make_request(self, request: Request) -> Response:
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, data=data)


class AnotherToyClient(Client):
    async def make_request(self, request: Request) -> Response:
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, data=data)
