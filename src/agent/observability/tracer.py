from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Span:
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def finish(self) -> None:
        self.end_time = time.time()


class Tracer:
    def __init__(self) -> None:
        self.spans: list[Span] = []

    def start_span(self, name: str, metadata: dict[str, object] | None = None) -> Span:
        span = Span(name=name, metadata=metadata or {})
        self.spans.append(span)
        return span

    def get_trace(self) -> list[dict[str, object]]:
        return [
            {
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "duration": None if span.end_time is None else span.end_time - span.start_time,
                "metadata": span.metadata,
            }
            for span in self.spans
        ]
