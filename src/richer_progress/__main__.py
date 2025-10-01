"""
Entry point for richer_progress.

Demonstrates usage when run as a script.
"""

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

    from . import Progress

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
