"""Background worker that normalizes a batch of WAV files (Qt side).

Wraps :class:`vat.audio.normalizer.Normalizer` for use from a ``QThread``:
the UI connects ``progress`` to a progress dialog, ``finished`` to a summary,
and calls :meth:`cancel` from the dialog's Cancel button. The worker never
touches the originals; it only writes the destinations it was given.
"""

from __future__ import annotations

import logging
from typing import List, Sequence, Tuple

from PySide6.QtCore import QObject, Signal

from vat.audio.normalizer import Normalizer, NormalizeResult


class NormalizeBatchWorker(QObject):
    #: (index, total, name) before each file starts.
    progress = Signal(int, int, str)
    #: The list of NormalizeResult, one per file attempted (also after a cancel).
    finished = Signal(object)
    #: An unexpected failure of the batch itself (not of a single file).
    failed = Signal(str)
    #: Always emitted last, for the owning QThread to quit on.
    done = Signal()

    def __init__(self, normalizer: Normalizer, pairs: Sequence[Tuple[str, str]]):
        super().__init__()
        self.normalizer = normalizer
        self.pairs = list(pairs)
        self.results: List[NormalizeResult] = []

    @property
    def canceled(self) -> bool:
        return self.normalizer.canceled

    def cancel(self) -> None:
        self.normalizer.cancel()

    def run(self) -> None:
        try:
            self.results = self.normalizer.normalize_many(
                self.pairs,
                progress=lambda i, n, name: self.progress.emit(i, n, name),
            )
            self.finished.emit(list(self.results))
        except Exception as e:  # pragma: no cover - defensive
            logging.exception("normalize batch failed")
            self.failed.emit(str(e))
        finally:
            self.done.emit()


__all__ = ["NormalizeBatchWorker"]
