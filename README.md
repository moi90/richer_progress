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

MIT License

Copyright (c) 2025 Simon-Martin Schröder

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
