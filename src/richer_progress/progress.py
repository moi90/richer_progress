from __future__ import annotations

import threading
from typing import Callable, cast

import humanize
import rich.progress
import rich.text

from .multiprocessing import ProxyServer, lookup_progress, lookup_task


class PrefixedMofNCompleteColumn(rich.progress.MofNCompleteColumn):
    def render(self, task) -> rich.text.Text:
        """Show completed/total."""
        total = humanize.metric(task.total) if task.total is not None else "?"
        total_width = len(str(total))
        completed = humanize.metric(task.completed)
        return rich.text.Text(
            f"{completed:>{total_width}}{self.separator}{total}",
            style="progress.download",
        )


class Task[T_work: int | float]:
    def __init__(
        self,
        progress: Progress,
        work_expected: T_work | None,
        progress_bar_task_id: rich.progress.TaskID | None,
        transient: bool,
    ):
        self.progress = progress
        self.work_expected = work_expected
        self.progress_bar_task_id = progress_bar_task_id
        self.transient = transient

        self.work_completed: T_work = cast(T_work, 0)

        self._id: int | None = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop(exc_type is not None)

    def update(self, delta: T_work | None = None, work_expected: T_work | None = None):
        """Update the task's progress or expected amount of work."""
        if delta is not None:
            self.work_completed = self.work_completed + delta  # type: ignore
        if work_expected is not None:
            self.work_expected = work_expected

        self.progress._update_progress_bar(self)

    def start(self):
        self.progress._start_task(self)

    def cancel(self):
        """Cancel the task."""
        self.stop(cancelled=True)

    def stop(self, cancelled: bool = False):
        """Finalize the task, marking it as completed or cancelled."""
        self.progress._stop_task(self, cancelled, self.transient)

        if self._id is not None:
            server = ProxyServer()
            server.unregister_task(self._id)
            self._id = None

    def range(self, *args):
        """Yield numbers in range, updating progress."""

        for i in range(*args):
            yield i
            self.update(1)  # type: ignore

    def enumerate(self, iterable):
        """Yield (index, item) pairs from iterable, updating progress."""

        for i, item in enumerate(iterable):
            yield i, item
            self.update(1)  # type: ignore

    def __reduce__(self) -> tuple[Callable, tuple]:
        # Serialize the task for multiprocessing
        server = ProxyServer()

        # Don't register the task multiple times
        if self._id is None:
            self._id = server.register_task(self)

        # `lookup_task` will create a proxy to the task
        return (
            lookup_task,
            (
                server.address,
                self._id,
            ),
        )

    def _get_work_completed(self) -> T_work:
        return self.work_completed

    def _get_work_expected(self) -> T_work | None:
        return self.work_expected


class Progress[T_work: int | float]:
    def __init__(
        self,
        n_tasks: int | Progress[int] | None = None,
        *,
        progress_bar: rich.progress.Progress | None = None,
        overall_description: str | None = None,
    ):
        if not (
            n_tasks is None or isinstance(n_tasks, (int, Progress))
        ):  # pragma: no cover
            raise ValueError("n_tasks must be an int or another Progress instance")

        self.n_tasks_completed: int = 0
        self.n_tasks_cancelled: int = 0
        self.active_tasks: list[Task] = []
        self.work_completed: T_work = cast(T_work, 0)

        self.n_tasks = n_tasks
        self._progress_bar = progress_bar

        if self._progress_bar is not None and overall_description is not None:
            self._overall_progress_id = self._progress_bar.add_task(
                overall_description, total=None
            )
        else:
            self._overall_progress_id = None

        self._lock = threading.RLock()
        self._id: int | None = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def start(self):
        if self._progress_bar is not None:
            self._progress_bar.start()

    def stop(self):
        with self._lock:
            # Cancel all active tasks (may happen if the main process exits before all tasks are done)
            for task in list(self.active_tasks):  # pragma: no cover
                task.cancel()

            # Stop the progress bar
            if self._progress_bar is not None:
                self._progress_bar.stop()

            # Unregister from the ProxyServer
            if self._id is not None:
                server = ProxyServer()
                server.unregister_progress(self._id)
                self._id = None

    def add_task(
        self,
        work_expected: T_work | None = None,
        *,
        description: str | None = None,
        transient=True,
    ) -> Task[T_work]:
        with self._lock:
            # Create a progress bar if needed
            if self._progress_bar is not None and description is not None:
                progress_bar_task_id = self._progress_bar.add_task(
                    description, total=work_expected
                )
            else:
                progress_bar_task_id = None

            task = Task(self, work_expected, progress_bar_task_id, transient)
            self.active_tasks.append(task)

            # Update the overall progress bar with the new total expected work
            self._update_progress_bar()

            return task

    def add_cancelled_task(self):
        """
        Add a cancelled task.

        Shortform for `add_task().cancel()`.
        """
        with self._lock:
            self.n_tasks_cancelled += 1

    def _start_task(self, task: Task[T_work]):
        with self._lock:
            if self._progress_bar is not None and task.progress_bar_task_id is not None:
                self._progress_bar.start_task(task.progress_bar_task_id)

    def _stop_task(self, task: Task[T_work], cancelled: bool, transient: bool):
        with self._lock:
            try:
                self.active_tasks.remove(task)
            except ValueError:
                # Task was already removed
                return

            if cancelled:
                self.n_tasks_cancelled += 1
            else:
                # Increment the number of completed tasks
                self.n_tasks_completed += 1
                # Update the total work completed
                self.work_completed += task.work_completed  # type: ignore

            if self._progress_bar is not None and task.progress_bar_task_id is not None:
                if transient:
                    self._progress_bar.remove_task(task.progress_bar_task_id)
                else:
                    self._progress_bar.stop_task(task.progress_bar_task_id)

    def _update_progress_bar(self, task: Task | None = None):
        with self._lock:
            if self._progress_bar is None:
                return

            # Update the individual task's progress bar
            if task is not None and task.progress_bar_task_id is not None:
                self._progress_bar.update(
                    task.progress_bar_task_id,
                    completed=task.work_completed,
                    total=task.work_expected,
                )

            # Update the overall progress bar
            if self._overall_progress_id is not None:
                self._progress_bar.update(
                    self._overall_progress_id,
                    completed=self.work_completed
                    + sum(t.work_completed for t in self.active_tasks),
                    total=self.work_expected,
                )

    def _get_work_expected(self) -> T_work | None:
        """Get the expected total amount of work of all tasks."""
        with self._lock:
            n_tasks: int | None = (
                self.n_tasks.work_expected
                if isinstance(self.n_tasks, Progress)
                else self.n_tasks
            )

            if n_tasks is None:
                return None

            # Adjust n_tasks to account for cancelled tasks which no longer contribute
            # to the expected total number of tasks
            n_tasks -= self.n_tasks_cancelled

            # Calculate the number of tasks with known expected work
            n_tasks_known = self.n_tasks_completed + sum(
                1 for t in self.active_tasks if t.work_expected is not None
            )

            if n_tasks_known == 0:
                return None

            # Adjust n_tasks to be at least the number of known tasks
            n_tasks = max(n_tasks, n_tasks_known)

            # Sum the expected work of all known tasks
            total_work_expected = self.work_completed + sum(
                t.work_expected
                for t in self.active_tasks
                if t.work_expected is not None
            )

            # Scale the total expected work to account for unknown tasks
            return type(total_work_expected)(
                total_work_expected * n_tasks / n_tasks_known
            )  # type: ignore

    work_expected = property(_get_work_expected)

    def _get_work_completed(self):
        return self.work_completed

    def __reduce__(self) -> tuple[Callable, tuple]:
        # Serialize the progress instance for multiprocessing
        server = ProxyServer()

        # Don't register the progress instance multiple times
        if self._id is None:
            self._id = server.register_progress(self)

        # `lookup_progress` will create a proxy to the progress instance
        return (
            lookup_progress,
            (
                server.address,
                self._id,
            ),
        )
