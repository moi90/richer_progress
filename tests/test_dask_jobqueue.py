import multiprocessing.process
import os
import secrets

import pytest

from richer_progress import Progress
from richer_progress.multiprocessing import ProxyServer
from richer_progress.testing import single_task_job

# Skip the test if Dask 'dask_jobqueue' or 'distributed' is not installed
pytest.importorskip("dask_jobqueue")
pytest.importorskip("distributed")


def test_with_SLURM(pytestconfig):
    from dask_jobqueue.slurm import SLURMCluster
    from distributed import Client

    queue = pytestconfig.getoption("slurm_queue")
    account = pytestconfig.getoption("slurm_account")
    interface = pytestconfig.getoption("slurm_interface")

    if queue is None:
        pytest.skip("No SLURM queue specified, skipping SLURM test")

    # Configure ProxyServer to use a public interface
    ProxyServer.configure(interface=interface)

    # Generate a random authkey for the main process and all workers
    authkey = secrets.token_hex(32)
    os.environ["MULTIPROCESSING_AUTHKEY"] = authkey
    multiprocessing.process.current_process().authkey = authkey.encode("ascii")

    with (
        SLURMCluster(
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
        # Setup authkey for worker processes
        from richer_progress.distributed import AuthkeyFromEnvPlugin

        client.register_plugin(AuthkeyFromEnvPlugin())

        print("Scaling SLURM cluster to 1 worker...")
        cluster.scale(1)

        print("Submitting task to SLURM cluster...")
        future = client.submit(single_task_job, progress, 5)

        print("Waiting for task to complete...")
        task_work_completed = future.result()

        assert task_work_completed == 5
        assert progress.n_tasks == 1
        assert progress.work_expected == 5
        assert progress.work_completed == 5
