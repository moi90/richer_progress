# richer-progress

A progress-tracking library built on top of [rich.progress](https://rich.readthedocs.io/en/stable/progress.html).

`richer_progress` is designed for workloads where progress is **hierarchical** and the **total amount of work is only gradually revealed**.  
It provides a clean API for tracking tasks, their sizes, completions, and failures — and integrates seamlessly with Rich's beautiful progress bars.

## What makes richer_progress special?

`richer_progress` extends `rich.progress` with features for **dynamic, nested, and evolving workloads**:

- **Hierarchical progress tracking:** Track progress across multiple levels (e.g. projects → files → bytes), aggregating completion at each level.
- **Dynamic task discovery:** Add tasks as they are found, even after progress tracking has started.
- **Unknown totals:** Start tracking without knowing the full workload size; update totals as new information arrives.
- **Consistent units:** Track progress in consistent units across all tasks and levels.
- **Flexible updates:** Adjust expected totals, add or remove tasks, and handle failures gracefully.
- **Rich integration:** All features work seamlessly with Rich's live, colorful progress rendering.
- **Multiprocessing capabilities:** Effortlessly track and aggregate progress from multiple worker processes. `richer_progress` provides mechanisms for safe, real-time progress updates across process boundaries, making it suitable for distributed or parallel workloads.

## License

[MIT License](LICENSE)
