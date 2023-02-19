def test_requests_worker_init(requests_worker, clients):
    """Test init method in RequestsWorker maps clients correctly"""
    client_name, client = next(iter(requests_worker.clients.items()))
    assert client_name == clients[0].get_name()
    assert client == clients[0]

