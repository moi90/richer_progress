import os
import distributed.diagnostics.plugin


class AuthkeyFromEnvPlugin(distributed.diagnostics.plugin.WorkerPlugin):
    """
    A Dask WorkerPlugin to set the authkey for multiprocessing on the worker process.

    By default, `sbatch` forwards all of the user's environment to the job.
    """

    def setup(self, worker):
        import multiprocessing.process

        print("Setting authkey on worker process")

        multiprocessing.process.current_process().authkey = os.environ[
            "MULTIPROCESSING_AUTHKEY"
        ].encode("ascii")
