from __future__ import annotations

import threading
from typing import Callable, cast

import humanize
import rich.progress
import rich.text


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

        self.progress._update(self)

    def start(self):
        self.progress._start_task(self)

    def cancel(self):
        """Cancel the task."""
        self.stop(cancelled=True)

    def stop(self, cancelled: bool = False):
        """Finalize the task, marking it as completed or cancelled."""
        self.progress._stop_task(self, cancelled, self.transient)

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
        # TODO: Implement serialization for multiprocessing
        ...


class Progress[T_work: int | float]:
    def __init__(
        self,
        n_tasks: int | Progress[int],
        *,
        progress_bar: rich.progress.Progress | None = None,
        overall_description: str | None = None,
    ):
        if not isinstance(n_tasks, (int, Progress)):
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
            # Cancel all active tasks
            for task in list(self.active_tasks):
                task.cancel()

            if self._progress_bar is not None:
                self._progress_bar.stop()

    def add_task(
        self,
        work_expected: T_work = 1,
        *,
        description: str | None = None,
        transient=True,
    ) -> Task[T_work]:
        with self._lock:
            if self._progress_bar is not None and description is not None:
                progress_bar_task_id = self._progress_bar.add_task(
                    description, total=work_expected
                )
            else:
                progress_bar_task_id = None

            task = Task(self, work_expected, progress_bar_task_id, transient)
            self.active_tasks.append(task)
            return task

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

    def _update(self, task: Task | None = None):
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

    @property
    def work_expected(self) -> T_work | None:
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

    def __rich_console__(self, console, options):
        if self._progress_bar is not None and self._progress_bar.tasks:
            yield self._progress_bar

    def __reduce__(self) -> tuple[Callable, tuple]:
        # TODO: Implement serialization for multiprocessing
        ...


if __name__ == "__main__":
    # Demonstrate usage
    import random
    import time

    from rich.progress import (
        BarColumn,
        DownloadColumn,
        MofNCompleteColumn,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.progress import (
        Progress as RichProgress,
    )

    # A hierarchy of projects / files / bytes
    n_projects = random.randint(5, 15)
    with (
        # Estimate the number of projects
        Progress(
            n_projects,
            overall_description="Projects",
            progress_bar=RichProgress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(compact=True),
            ),
        ) as all_projects,
        Progress(
            n_tasks=all_projects,
            overall_description="Files (total)",
            progress_bar=RichProgress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(compact=True),
            ),
        ) as all_files,
        Progress(
            n_tasks=all_files,
            overall_description="Bytes (total)",
            progress_bar=RichProgress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(compact=True),
            ),
        ) as all_bytes,
    ):
        print(f"Processing {n_projects} projects...")
        for project_id in range(n_projects):
            with all_projects.add_task(1) as project_task:
                project_may_fail = project_id % 3 == 0

                try:
                    n_files = random.randint(5, 15)

                    with all_files.add_task(
                        n_files,
                        description=f"Files for {project_id}",
                    ) as project_files:
                        for file_id in project_files.range(n_files):
                            n_bytes = random.randint(500, 1000)

                            with all_bytes.add_task(
                                n_bytes,
                                description=f"Copy {project_id}/{file_id}",
                            ) as file_bytes:
                                for i in file_bytes.range(n_bytes):
                                    if project_may_fail and random.random() < 0.001:
                                        raise ValueError(
                                            f"Error at {project_id}/{file_id} byte {i}!"
                                        )

                                    time.sleep(0.0001)  # Simulate work
                except ValueError as e:
                    print(f"Error processing project {project_id}: {e}")
                    project_task.cancel()
                else:
                    project_task.update(1)
