"""Review statistics tracking and grading."""

import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ItemStats:
    """Statistics for a single item."""
    item_id: str
    media_type: str  # "image" or "video"
    media_path: str
    wav_path: str
    wrong_guesses: int = 0
    time_to_correct_sec: float = 0.0
    overtime: bool = False
    timeout: bool = False
    attempts: int = 0
    play_count_served: int = 0
    confirm_method: str = ""  # "mouse", "keyboard", "timeout"
    notes: str = ""


class ReviewStats:
    """Tracks per-item and aggregate statistics for review sessions.
    
    Grading formula:
    - Accuracy (A): correct / total
    - Time efficiency (Ts): clamp((Tmax - (avg_time - baseline)) / (Tmax - Topt), 0, 1)
      where Topt = 2s, Tmax = 10s
    - Composite score (S): (1 - w) * A + w * Ts, where w is time weighting
    - Letter grade: A+ >= 0.95, A >= 0.90, B+ >= 0.80, B >= 0.75,
                    C+ >= 0.70, C >= 0.65, D >= 0.55, else F
    """
    
    # Grading constants
    TOPT = 2.0  # Optimal time in seconds
    TMAX = 10.0  # Maximum time in seconds
    
    GRADE_THRESHOLDS = {
        "A+": 0.95,
        "A": 0.90,
        "B+": 0.80,
        "B": 0.75,
        "C+": 0.70,
        "C": 0.65,
        "D": 0.55,
    }
    
    def __init__(self):
        self._items: Dict[str, ItemStats] = {}
        self._prompt_history: List[Tuple[str, float, bool, str]] = []  # (item_id, time, correct, method)
        self._session_start_time: Optional[float] = None
        self._current_prompt_start: Optional[float] = None
        self._paused_time: float = 0.0
        self._pause_start: Optional[float] = None
    
    def start_session(self) -> None:
        """Start a new session."""
        self._session_start_time = time.time()
        self._prompt_history = []
        self._paused_time = 0.0
        self._pause_start = None
    
    def add_item(self, item_id: str, media_type: str, media_path: str, wav_path: str) -> None:
        """Add an item to track."""
        if item_id not in self._items:
            self._items[item_id] = ItemStats(
                item_id=item_id,
                media_type=media_type,
                media_path=media_path,
                wav_path=wav_path,
            )
    
    def start_prompt(self, item_id: str) -> None:
        """Start timing for a prompt."""
        self._current_prompt_start = time.time()
        if item_id in self._items:
            self._items[item_id].play_count_served += 1
    
    def pause_timer(self) -> None:
        """Pause the current prompt timer (e.g., during fullscreen video)."""
        if self._current_prompt_start is not None and self._pause_start is None:
            self._pause_start = time.time()
    
    def resume_timer(self) -> None:
        """Resume the current prompt timer."""
        if self._pause_start is not None:
            self._paused_time += time.time() - self._pause_start
            self._pause_start = None
    
    def record_response(
        self,
        item_id: str,
        correct: bool,
        confirm_method: str = "mouse",
        overtime: bool = False,
        timeout: bool = False,
    ) -> None:
        """Record a response for an item.
        
        Args:
            item_id: Item identifier
            correct: Whether the response was correct
            confirm_method: "mouse", "keyboard", or "timeout"
            overtime: Whether the response exceeded the soft time limit
            timeout: Whether the response timed out (hard limit)
        """
        if item_id not in self._items:
            return
        
        item = self._items[item_id]
        item.attempts += 1
        
        # Calculate elapsed time
        elapsed = 0.0
        if self._current_prompt_start is not None:
            # Ensure timer is not paused
            if self._pause_start is not None:
                self.resume_timer()
            
            elapsed = time.time() - self._current_prompt_start - self._paused_time
            self._paused_time = 0.0
            self._current_prompt_start = None
        
        if not correct:
            item.wrong_guesses += 1
        else:
            # Only record time to correct on first correct answer
            if item.time_to_correct_sec == 0.0:
                item.time_to_correct_sec = elapsed
                item.confirm_method = confirm_method
                item.overtime = overtime
                item.timeout = timeout
        
        # Record in history
        self._prompt_history.append((item_id, elapsed, correct, confirm_method))
    
    def get_overall_stats(
        self,
        time_weighting: float = 0.3,
        ui_overhead_sec: float = 0.6,
    ) -> Dict[str, Any]:
        """Calculate overall session statistics.
        
        Args:
            time_weighting: Weight of time in composite score (0-1)
            ui_overhead_sec: UI overhead to subtract from times
        
        Returns:
            Dictionary with overall statistics
        """
        total_items = len(self._items)
        total_prompts = len(self._prompt_history)
        total_correct = sum(1 for _, _, correct, _ in self._prompt_history if correct)
        total_wrong = total_prompts - total_correct
        
        # Count timeouts and overtimes
        timeouts = sum(1 for item in self._items.values() if item.timeout)
        overtime_count = sum(1 for item in self._items.values() if item.overtime)
        
        # Calculate accuracy
        accuracy = total_correct / total_prompts if total_prompts > 0 else 0.0
        
        # Calculate time efficiency
        times = [t - ui_overhead_sec for _, t, correct, _ in self._prompt_history if correct and t > 0]
        times = [max(0.0, t) for t in times]  # Clamp to non-negative
        
        avg_time = sum(times) / len(times) if times else 0.0
        median_time = sorted(times)[len(times) // 2] if times else 0.0
        
        # Time efficiency score: Ts = clamp((Tmax - avg_time) / (Tmax - Topt), 0, 1)
        time_efficiency = 0.0
        if avg_time > 0:
            time_efficiency = (self.TMAX - avg_time) / (self.TMAX - self.TOPT)
            time_efficiency = max(0.0, min(1.0, time_efficiency))
        
        # Composite score: S = (1 - w) * A + w * Ts
        composite_score = (1 - time_weighting) * accuracy + time_weighting * time_efficiency
        
        # Determine letter grade
        grade = "F"
        for letter, threshold in sorted(self.GRADE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if composite_score >= threshold:
                grade = letter
                break
        
        return {
            "totalItems": total_items,
            "totalPrompts": total_prompts,
            "totalCorrect": total_correct,
            "totalWrong": total_wrong,
            "timeouts": timeouts,
            "overtimeCount": overtime_count,
            "accuracyPercent": round(accuracy * 100, 2),
            "averageTimeSec": round(avg_time, 2),
            "medianTimeSec": round(median_time, 2),
            "timeEfficiencyScore": round(time_efficiency, 3),
            "compositeScore": round(composite_score, 3),
            "grade": grade,
        }
    
    def get_item_stats(self) -> List[ItemStats]:
        """Get statistics for all items."""
        return list(self._items.values())
    
    def get_trouble_items(self) -> List[str]:
        """Get items sorted by longest time then most wrong guesses.
        
        Returns:
            List of item IDs
        """
        items = list(self._items.values())
        # Sort by time_to_correct (descending), then wrong_guesses (descending)
        items.sort(key=lambda x: (-x.time_to_correct_sec, -x.wrong_guesses))
        return [item.item_id for item in items if item.time_to_correct_sec > 0 or item.wrong_guesses > 0]
