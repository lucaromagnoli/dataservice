import pytest

from dataservice.service import RequestWorker
from tests.clients import ToyClient, AnotherToyClient


def test_requests_worker_init(requests_worker, clients):
    """Test init method in RequestsWorker maps clients correctly"""
    client_name, client = next(iter(requests_worker.clients.items()))
    assert client_name == clients[0].get_name()
    assert client == clients[0]


@pytest.mark.parametrize(
    "clients",
    [
        pytest.param((ToyClient(),), id="One single client"),
        pytest.param((ToyClient(), AnotherToyClient()), id="Two clients"),
    ],
)
def test_requests_worker_main_client(requests_worker, clients):
    """Test RequestsWorker get_main_client"""
    assert requests_worker.get_main_client() == clients[0]


@pytest.mark.parametrize(
    "clients, client_name, expected",
    [
        pytest.param((ToyClient(),), "ToyClient", ToyClient, id="One Single Client"),
        pytest.param(
            (ToyClient(), AnotherToyClient()), "ToyClient", ToyClient, id="Two clients"
        ),
        pytest.param(
            (ToyClient(), AnotherToyClient()),
            "AnotherToyClient",
            AnotherToyClient,
            id="Two clients",
        ),
        pytest.param(
            (ToyClient(), AnotherToyClient()),
            "HTPPXClient",
            ToyClient,
            id="Two clients, the requested clients doesn't exists. Fallback to ToyClient",
        ),
    ],
)
def test_requests_worker_get_client_by_name(clients, client_name, expected):
    requests_worker = RequestWorker(clients)
    client = requests_worker.get_client_by_name(client_name)
    assert isinstance(client, expected)
