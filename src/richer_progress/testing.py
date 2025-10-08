import time
from .progress import Progress


def single_task_job(progress: Progress, size: int, sleep=0.0) -> int:
    try:
        print("single_task_job: Adding task...")
        with progress.add_task(size, description="dask worker") as task:
            print("single_task_job: Processing task...")
            for _ in task.range(size):
                if sleep > 0:
                    time.sleep(sleep)

        return task.work_completed
    finally:
        print("single_task_job: Done.")
