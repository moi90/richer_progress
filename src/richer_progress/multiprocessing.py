import atexit
import functools
import inspect
import logging
import os
import threading
import uuid
from multiprocessing.managers import BaseManager, BaseProxy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .progress import Progress, Task

logger = logging.getLogger(__name__)


def _warn_fork():
    logger.warning(
        "Warning: fork() has been called. "
        "richer_progress will not work correctly in the child process. "
        "Use the 'spawn' start method for multiprocessing instead."
    )


os.register_at_fork(before=_warn_fork, after_in_child=_warn_fork)


class ParameterSingletonMeta(type):
    _lock = threading.Lock()
    _instances = {}

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            bound_args = inspect.signature(cls.__init__).bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            key = (cls, tuple(bound_args.arguments.items()))

            try:
                return cls._instances[key]
            except KeyError:
                pass

            instance = cls._instances[key] = super().__call__(*args, **kwargs)

            return instance


class ProxyServer(metaclass=ParameterSingletonMeta):
    def __init__(self):
        class ProgressManager(BaseManager):
            pass

        ProgressManager.register(
            "Progress", callable=self._lookup_progress, proxytype=ProgressProxy
        )
        ProgressManager.register(
            "Task", callable=self._lookup_task, proxytype=TaskProxy
        )

        self._progress_manager = ProgressManager()
        server = self._progress_manager.get_server()

        self.address = server.address
        self.authkey = bytes(server.authkey)  # type: ignore

        # Start the server in a background thread
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def _shutdown():
            try:
                server.stop_event.set()  # type: ignore
            except Exception:
                pass

        atexit.register(_shutdown)

        self._processes: dict[int, object] = {}
        self._tasks: dict[int, object] = {}
        self._lock = threading.Lock()

    def register_progress(self, progress: "Progress") -> int:
        with self._lock:
            if progress in self._processes.values():
                raise ValueError("Progress instance is already registered")

            id = uuid.uuid4().int

            self._processes[id] = progress

            print(f"Registered progress {id}: {progress}")

            return id

    def unregister_progress(self, progress_id: int) -> None:
        with self._lock:
            self._processes.pop(progress_id, None)

    def register_task(self, task: "Task") -> int:
        with self._lock:
            if task in self._tasks.values():
                raise ValueError("Task instance is already registered")

            id = uuid.uuid4().int

            self._tasks[id] = task

            print(f"Registered task {id}: {task}")

            return id

    def unregister_task(self, task_id: int) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)

    def _lookup_progress(self, progress_id: int):
        with self._lock:
            return self._processes[progress_id]

    def _lookup_task(self, task_id: int):
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as e:
                e.add_note(f"self._tasks.keys(): {list(self._tasks.keys())}")
                raise e


class TaskProxy(BaseProxy):
    _exposed_ = (
        "start",
        "stop",
        "cancel",
        "update",
        "_get_work_expected",
        "_get_work_completed",
    )

    def start(self) -> None:
        return self._callmethod("start")

    def stop(self, cancelled: bool = False):
        return self._callmethod("stop", (cancelled,))

    def cancel(self) -> None:
        return self._callmethod("cancel")

    def update(self, *args, **kwargs) -> None:
        return self._callmethod("update", args, kwargs)

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

    @property
    def work_completed(self) -> int:
        return self._callmethod("_get_work_completed")

    @property
    def work_expected(self) -> int | None:
        return self._callmethod("_get_work_expected")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class ProgressProxy(BaseProxy):
    _exposed_ = ("add_task",)

    def add_task(self, *args, **kwargs) -> TaskProxy:
        return self._callmethod("add_task", args, kwargs)


class _ProxyClient:
    def __init__(self, address, authkey) -> None:
        class ProgressManager(BaseManager):
            pass

        ProgressManager.register("Progress", proxytype=ProgressProxy)
        ProgressManager.register("Task", proxytype=TaskProxy)

        self._client = ProgressManager(address=address, authkey=authkey)
        self._client.connect()

    def lookup_progress(self, progress_id: int) -> "Progress":
        return self._client.Progress(progress_id)

    def lookup_task(self, task_id: int) -> "Task":
        return self._client.Task(task_id)


@functools.cache
def ProxyClient(address, authkey) -> _ProxyClient:
    return _ProxyClient(address, authkey)


def lookup_task(address, authkey, task_id):
    return ProxyClient(address, authkey).lookup_task(task_id)


def lookup_progress(address, authkey, progress_id):
    return ProxyClient(address, authkey).lookup_progress(progress_id)
