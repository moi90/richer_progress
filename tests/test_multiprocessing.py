from richer_progress.multiprocessing import ProxyClient, ProxyServer
from richer_progress.progress import Progress, Task


def test_proxy_server_singleton():
    server1 = ProxyServer()
    server2 = ProxyServer()
    assert server1 is server2, "ProxyServer should be a singleton"


def test_register_and_lookup_progress():
    server = ProxyServer()
    progress = Progress(1)
    progress_id = server.register_progress(progress)
    looked_up_progress = server._lookup_progress(progress_id)
    assert looked_up_progress is progress, (
        "Looked up Progress should match the registered instance"
    )


def test_register_and_lookup_task():
    server = ProxyServer()
    progress = Progress(1)
    task = progress.add_task(10, description="foo")
    task_id = server.register_task(task)
    looked_up_task = server._lookup_task(task_id)
    assert looked_up_task is task, "Looked up Task should match the registered instance"


def test_proxy_client_lookup_progress_singleprocess():
    server = ProxyServer()
    progress = Progress(1)
    progress_id = server.register_progress(progress)

    client = ProxyClient(server.address, server.authkey)
    looked_up_progress = client.lookup_progress(progress_id)

    looked_up_progress.add_task(5, description="bar")

    assert progress.n_tasks == 1, (
        "Progress instance on server should reflect changes made via proxy client"
    )


def test_proxy_client_lookup_task_singleprocess():
    server = ProxyServer()
    progress = Progress(1)
    task = progress.add_task(10, description="foo")
    task_id = server.register_task(task)

    client = ProxyClient(server.address, server.authkey)
    looked_up_task = client.lookup_task(task_id)

    looked_up_task.update(delta=5)

    assert task.work_completed == 5, (
        "Task instance on server should reflect changes made via proxy client"
    )


def _test_proxy_client_lookup_task_multiprocess_worker(address, authkey, task_id):
    client = ProxyClient(address, authkey)
    looked_up_task = client.lookup_task(task_id)
    with looked_up_task:
        for _ in looked_up_task.range(5):
            pass  # Simulate work
    assert looked_up_task.work_completed == 5


def test_proxy_client_lookup_task_multiprocess():
    import multiprocessing

    server = ProxyServer()
    progress = Progress(1)
    task = progress.add_task(10, description="foo")
    task_id = server.register_task(task)

    p = multiprocessing.get_context("spawn").Process(
        target=_test_proxy_client_lookup_task_multiprocess_worker,
        args=(server.address, server.authkey, task_id),
    )
    p.start()
    p.join()

    assert task.work_completed == 5, (
        "Task instance on server should reflect changes made in worker process"
    )
    assert progress.work_completed == 5, (
        "Progress instance on server should reflect changes made in worker process"
    )
