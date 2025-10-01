from richer_progress import Progress


def test_task_not_completed():
    with Progress(1) as progress:
        # While were in a task, the total size should reflect the expected size of the task
        with progress.add_task(10, description="foo"):
            assert progress.work_expected == 10
            assert isinstance(progress.work_expected, int)

        # If no work was actually completed in a task (that finished),
        # the expected total amount of work is zero
        assert progress.work_expected == 0


def test_task_completed():
    with Progress(1) as progress:
        # While were in a task, the total size should reflect the expected size of the task
        with progress.add_task(10, description="foo") as task:
            assert progress.work_expected == 10
            assert isinstance(progress.work_expected, int)

            # Complete some work
            task.update(delta=5)

        # The expected total amount of work should now be the amount of work that was actually completed
        assert progress.work_expected == 5
        assert progress.work_completed == 5


def test_task_cancel():
    with Progress(1) as progress:
        # While were in a task, the total size should reflect the expected size of the task
        with progress.add_task(10, description="foo") as task:
            assert progress.work_expected == 10
            assert isinstance(progress.work_expected, int)

            # First, complete some work
            task.update(delta=5)

            # Now cancel the task
            task.cancel()

        # A cancelled task should not contribute to the total expected or completed work
        assert progress.n_tasks_completed == 0
        assert progress.n_tasks_cancelled == 1
        assert progress.work_expected is None
        assert progress.work_completed == 0
