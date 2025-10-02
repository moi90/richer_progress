import pytest


@pytest.fixture(autouse=True)
def clear_singletons():
    from richer_progress.multiprocessing import ProxyServer, ProxyClient

    ProxyServer.clear_instances()
    ProxyClient.clear_instances()
