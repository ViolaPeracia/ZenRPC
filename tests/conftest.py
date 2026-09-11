import pytest


class MockRPC:
    """In-memory mock for pypresence.Presence to test Discord RPC without Discord running."""

    def __init__(self, client_id):
        self.client_id = str(client_id)
        self.connected = False
        self.closed = False
        self.updates = []
        self.cleared = False
        self.connect_calls = 0
        self.fail_connect = False
        self.fail_update = False

    def connect(self):
        self.connect_calls += 1
        if self.fail_connect:
            raise ConnectionRefusedError("Simulated Discord connection failure")
        self.connected = True

    def update(self, **kwargs):
        if not self.connected:
            raise RuntimeError("Not connected to RPC")
        if self.fail_update:
            raise BrokenPipeError("Simulated Discord pipe broken")
        self.updates.append(kwargs)
        self.cleared = False

    def clear(self):
        self.cleared = True

    def close(self):
        self.connected = False
        self.closed = True


@pytest.fixture
def mock_rpc_factory():
    instances = []

    def _factory(client_id):
        rpc = MockRPC(client_id)
        instances.append(rpc)
        return rpc

    _factory.instances = instances
    return _factory
