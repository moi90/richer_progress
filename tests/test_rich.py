from io import StringIO

import pytest
from rich.console import Console
from rich.progress import (
    BarColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.progress import (
    Progress as RichProgress,
)

from richer_progress.progress import PrefixedMofNCompleteColumn, Progress


@pytest.mark.parametrize("transient_tasks", [True, False])
def test_overall_progress_bar(transient_tasks: bool):
    n_tasks = 5
    string_io = StringIO()
    console = Console(file=string_io)

    with Progress(
        n_tasks,
        overall_description="Tasks (total)",
        progress_bar=RichProgress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            PrefixedMofNCompleteColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(compact=True),
            console=console,
            auto_refresh=False,
        ),
    ) as all_tasks:
        assert all_tasks._progress_bar is not None

        for i in range(n_tasks):
            with all_tasks.add_task(
                10, description=f"task{i}", transient=transient_tasks
            ) as task:
                for _ in task.range(10):
                    pass
                assert task.progress_bar_task_id in all_tasks._progress_bar.task_ids

    output = string_io.getvalue()
    assert "Tasks (total)" in output
    for i in range(n_tasks):
        if transient_tasks:
            assert f"task{i}" not in output
        else:
            assert f"task{i}" in output
