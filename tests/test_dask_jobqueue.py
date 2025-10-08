import pytest
from richer_progress import Progress
import time
from richer_progress.multiprocessing import ProxyServer

# Skip the test if Dask 'dask_jobqueue' or 'distributed' is not installed
pytest.importorskip("dask_jobqueue")
pytest.importorskip("distributed")


def _worker(progress: Progress):
    try:
        print("_worker: Adding task...")
        with progress.add_task(5, description="dask worker") as task:
            print("_worker: Processing task...")
            for _ in range(5):
                time.sleep(0.01)

        return task.work_completed
    finally:
        print("_worker: Done.")


def test_with_SLURM(pytestconfig):
    from distributed import Client
    from dask_jobqueue import SLURMCluster

    queue = pytestconfig.getoption("slurm_queue")
    account = pytestconfig.getoption("slurm_account")
    interface = pytestconfig.getoption("slurm_interface")

    if queue is None:
        pytest.skip("No SLURM queue specified, skipping SLURM test")

    # Configure ProxyServer to use a public interface
    ProxyServer.configure(interface=interface)

    with (
        SLURMCluster(
            n_workers=1,
            memory="1g",
            processes=1,
            cores=1,
            queue=queue,
            account=account,
            interface=interface,
            name="richer-progress-test",
        ) as cluster,
        Client(cluster) as client,
        Progress(1) as progress,
    ):
        print("Waiting for workers to start...")
        client.wait_for_workers(1)

        print("Submitting task to SLURM cluster...")
        future = client.submit(_worker, progress)

        print("Waiting for task to complete...")
        task_work_completed = future.result()

        assert task_work_completed == 5
        assert progress.n_tasks == 1
        assert progress.work_expected == 5
        assert progress.work_completed == 5
