import pytest
from multiprocessing import Queue
from dataservice.models import Request, Response
from dataservice.service import SchedulerMixin, DataService

class TestSchedulerMixin:
    @pytest.fixture
    def scheduler_mixin(self):
        return SchedulerMixin()

    def test_enqueue_items(self, scheduler_mixin, mocker):
        mock_queue = mocker.MagicMock()
        items = [mocker.MagicMock(spec=Request), mocker.MagicMock(spec=Response)]
        scheduler_mixin._enqueue_items(items, mock_queue)
        mock_queue.put.assert_has_calls([mocker.call(items[0]), mocker.call(items[1])])

    def test_enqueue_requests(self, scheduler_mixin, mocker):
        mock_queue = mocker.MagicMock()
        requests = [mocker.MagicMock(spec=Request)]
        scheduler_mixin._enqueue_requests(requests, mock_queue)
        mock_queue.put.assert_called_once_with(requests[0])

    def test_enqueue_responses(self, scheduler_mixin, mocker):
        mock_queue = mocker.MagicMock()
        responses = [mocker.MagicMock(spec=Response)]
        scheduler_mixin._enqueue_responses(responses, mock_queue)
        mock_queue.put.assert_called_once_with(responses[0])

    def test_run_callables_in_pool_executor(self, scheduler_mixin, mocker):
        mock_executor = mocker.patch('dataservice.service.ProcessPoolExecutor')
        mock_callable = mocker.MagicMock()
        callables_and_args = [(mock_callable,)]
        scheduler_mixin.run_callables_in_pool_executor(callables_and_args, max_workers=1)
        mock_executor.assert_called_once_with(max_workers=1)
        mock_callable.assert_called_once()

class TestDataService:
    @pytest.fixture
    def data_service(self, clients):
        return DataService(clients)

    def test_run_processes(self, mocker, data_service):
        data_service.request_worker = mocker.MagicMock()
        data_service.response_worker = mocker.MagicMock()
        requests_queue = Queue()
        responses_queue = Queue()
        data_queue = Queue()
        data_service.run_callables_in_pool_executor = mocker.MagicMock()

        data_service._DataService__run_processes(requests_queue, responses_queue, data_queue)

        data_service.run_callables_in_pool_executor.assert_called_once()
        call_args = data_service.run_callables_in_pool_executor.call_args[0][0]
        assert call_args[0][0] == data_service.request_worker
        assert call_args[1][0] == data_service.response_worker

    def test_fetch(self, mocker, data_service):
        mock_manager = mocker.patch('dataservice.service.multiprocessing.Manager')
        mock_manager.return_value.__enter__.return_value.Queue.side_effect = [Queue(), Queue(), Queue()]
        requests = [mocker.MagicMock(spec=Request)]

        data_service._enqueue_requests = mocker.MagicMock()
        data_service._DataService__run_processes = mocker.MagicMock()

        data_service._DataService__fetch(requests)

        data_service._enqueue_requests.assert_called_once_with(requests, mock_manager.return_value.__enter__.return_value.Queue())
        data_service._DataService__run_processes.assert_called()