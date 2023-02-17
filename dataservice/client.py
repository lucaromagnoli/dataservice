from dataservice.http import Request, Response


class Client:
    async def make_request(self, request: Request) -> Response:
        return Response(request=request, data="response data")
