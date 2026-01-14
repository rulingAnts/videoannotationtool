"""Review queue management with fairness rules."""

import random
from typing import List, Tuple, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal


class ReviewQueue(QObject):
    """Manages randomized audio prompt queue with fairness guarantees.
    
    Fairness rules:
    - Shuffle without replacement per round
    - Multiple rounds if Play Count > 1
    - Rotate order across rounds to avoid positional bias
    - Prevent immediate repeats unless item count is too small
    
    Signals:
        promptReady(str, str): Emitted when a prompt is ready (item_id, wav_path)
        queueFinished(): Emitted when all prompts have been served
    """
    
    promptReady = Signal(str, str)  # item_id, wav_path
    queueFinished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[Tuple[str, str, str]] = []  # (item_id, media_path, wav_path)
        self._queue: List[Tuple[str, str, str]] = []
        self._current_index: int = 0
        self._seed: Optional[int] = None
    
    def build_queue(
        self,
        items: List[Tuple[str, str, str]],
        play_count: int = 1,
        seed: Optional[int] = None
    ) -> None:
        """Build a randomized queue from the given items.
        
        Args:
            items: List of (item_id, media_path, wav_path) tuples
            play_count: Number of times each item should appear
            seed: Optional random seed for reproducibility
        """
        self._items = list(items)
        self._seed = seed
        self._current_index = 0
        
        if not self._items:
            self._queue = []
            return
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Strategy: for small sets (<=6), use fully random order per prompt
        # while still respecting total play_count per item. For larger sets,
        # keep fairness guarantees (shuffle without replacement per round
        # with rotation and anti-repeat across rounds).
        small_set_threshold = 6
        if len(self._items) <= small_set_threshold:
            # Constrained random with replacement: choose randomly among items
            # that still have remaining appearances.
            remaining = {i: play_count for i in range(len(self._items))}
            self._queue = []
            total = len(self._items) * max(1, play_count)
            for _ in range(total):
                candidates = [idx for idx, cnt in remaining.items() if cnt > 0]
                if not candidates:
                    break
                pick = random.choice(candidates)
                self._queue.append(self._items[pick])
                remaining[pick] -= 1
        else:
            # Build queue with fairness guarantees
            if play_count == 1:
                # Single round: simple shuffle
                self._queue = list(self._items)
                random.shuffle(self._queue)
            else:
                # Multiple rounds: shuffle each round and rotate
                self._queue = []
                for round_num in range(play_count):
                    round_items = list(self._items)
                    random.shuffle(round_items)
                    
                    # Rotate to avoid positional bias
                    if round_num > 0:
                        rotation = round_num % len(round_items)
                        round_items = round_items[rotation:] + round_items[:rotation]
                    
                    # Prevent immediate repeats between rounds
                    if self._queue and len(round_items) > 1:
                        last_item = self._queue[-1]
                        if round_items[0] == last_item:
                            # Swap first with a random other position
                            swap_idx = random.randint(1, len(round_items) - 1)
                            round_items[0], round_items[swap_idx] = round_items[swap_idx], round_items[0]
                    
                    self._queue.extend(round_items)
        
        # Reset seed after queue building
        if seed is not None:
            random.seed()
    
    def next_prompt(self) -> Optional[Tuple[str, str, str]]:
        """Get the next prompt from the queue.
        
        Returns:
            Tuple of (item_id, media_path, wav_path) or None if queue is empty
        """
        if self._current_index >= len(self._queue):
            return None
        
        item = self._queue[self._current_index]
        self._current_index += 1
        return item
    
    def emit_next_prompt(self) -> bool:
        """Emit the next prompt signal.
        
        Returns:
            True if a prompt was emitted, False if queue is finished
        """
        item = self.next_prompt()
        if item is None:
            self.queueFinished.emit()
            return False
        
        item_id, media_path, wav_path = item
        self.promptReady.emit(item_id, wav_path)
        return True
    
    def get_progress(self) -> Tuple[int, int]:
        """Get current progress in the queue.
        
        Returns:
            Tuple of (current_index, total_count)
        """
        return (self._current_index, len(self._queue))
    
    def reset(self) -> None:
        """Reset the queue to the beginning."""
        self._current_index = 0
    
    def is_finished(self) -> bool:
        """Check if the queue is finished."""
        return self._current_index >= len(self._queue)
    
    def get_queue_metadata(self) -> Dict[str, Any]:
        """Get metadata about the current queue for export.
        
        Returns:
            Dictionary with strategy, rounds, and seed information
        """
        total_items = len(self._items)
        total_prompts = len(self._queue)
        rounds = total_prompts // total_items if total_items > 0 else 0
        
        return {
            "strategy": "shuffle_without_replacement_per_round",
            "rounds": rounds,
            "seed": self._seed,
        }
