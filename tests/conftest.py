import pytest


@pytest.fixture(autouse=True)
def clear_singletons():
    from richer_progress.multiprocessing import ProxyServer, ProxyClient

    ProxyServer.clear_instances()
    ProxyClient.clear_instances()


def pytest_addoption(parser):
    parser.addoption("--slurm-queue", default=None)
    parser.addoption("--slurm-account", default=None)
    parser.addoption("--slurm-interface", default=None)
