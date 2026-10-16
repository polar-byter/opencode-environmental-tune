"""Task-scoped quota supervision, including the coordinator, without a browser tab."""
import threading

from ..task_metrics import TaskMetrics


class QuotaMonitor:
    def __init__(self, root, reader, controls):
        self.root, self.reader, self.controls = root, reader, controls
        self.closed = threading.Event()
        self.thread = None

    def tick(self):
        folder = self.root / '.metrics'
        if not folder.is_dir():
            return
        for path in folder.iterdir():
            if self.closed.is_set():
                return
            if not path.is_dir() or not (path / 'events.jsonl').is_file():
                continue
            try:
                events = TaskMetrics(self.root).read(path.name)
                if not events[0].get('session') or any(e['kind'] == 'finish' for e in events):
                    continue
                state = self.controls.view(path.name)
                if state.get('status') not in (None, 'running'):
                    continue
                live = self.reader.view(self.root, events)
                if live.get('available'):
                    for signal in live.get('quota_errors', []):
                        self.controls.pause_for_limit(path.name, signal)
            except (OSError, ValueError, RuntimeError, TypeError, KeyError):
                # Observation failure is not a provider failure.
                continue

    def run(self):
        while not self.closed.is_set():
            try:
                self.tick()
            except (OSError, ValueError):
                pass
            self.closed.wait(2)

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.closed.set()
