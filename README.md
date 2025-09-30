# richer-progress

A progress-tracking library built on top of [rich.progress](https://rich.readthedocs.io/en/stable/progress.html).

`richer_progress` is designed for workloads where progress is **hierarchical** and the **total amount of work is only gradually revealed**.  
It provides a clean API for tracking tasks, their sizes, completions, and failures — and integrates seamlessly with Rich's beautiful progress bars.

## Why?

`rich.progress` is great when you know the total upfront (e.g. “download 1 GB”).  
But many real workloads look like this:

- You know the number of **projects**, but not how many **files** each contains until you start them.
- Each files may contain a different number of **bytes**.

With `richer_progress`, you can:

- Add tasks as they are discovered (`add_task(size)`).
- Track work completed vs work remaining in **consistent units**.
- Adjust the expected total when task sizes are discovered or tasks are dropped.
- Aggregate progress across multiple levels (projects → files → bytes).
- Still enjoy the live, colorful rendering of Rich.

## License

[MIT License](LICENSE)
