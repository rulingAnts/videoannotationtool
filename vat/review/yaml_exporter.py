"""YAML report exporter for review sessions."""

import os
import sys
import platform
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import yaml

from vat.review.stats import ReviewStats, ItemStats
from vat.review.session_state import ReviewSessionState
from vat.review.queue import ReviewQueue


class YAMLExporter:
    """Exports review session statistics to YAML format (English only).
    
    The YAML report includes:
    - version: report schema version
    - session: id, timestamp, language, appVersion
    - settings: all review settings
    - randomization: strategy, rounds, seed
    - overall: aggregate statistics
    - items: per-item results
    - troubleItems: sorted list of problematic items
    - environment: OS, platform, Python version, ffmpeg/ffprobe paths
    - export: grouped export settings if applicable
    """
    
    VERSION = "1.0"
    
    @staticmethod
    def export_session(
        stats: ReviewStats,
        state: ReviewSessionState,
        queue: ReviewQueue,
        session_id: str,
        language: str,
        app_version: str,
        output_dir: str,
        grouped_export_settings: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Export a review session to YAML.
        
        Args:
            stats: Review statistics
            state: Session state
            queue: Review queue
            session_id: Unique session identifier
            language: UI language (for reference, YAML is English-only)
            app_version: Application version
            output_dir: Directory to save the YAML file
            grouped_export_settings: Optional grouped export metadata
        
        Returns:
            Path to the created YAML file
        """
        # Build the report structure
        timestamp = datetime.now(timezone.utc)
        
        report = {
            "version": YAMLExporter.VERSION,
            "session": {
                "id": session_id,
                "timestamp": timestamp.isoformat(),
                "language": language,
                "appVersion": app_version,
            },
            "settings": YAMLExporter._export_settings(state),
            "randomization": queue.get_queue_metadata(),
            "overall": stats.get_overall_stats(
                time_weighting=state.timeWeightingPercent / 100.0,
                ui_overhead_sec=state.uiOverheadMs / 1000.0,
            ),
            "items": YAMLExporter._export_items(stats.get_item_stats()),
            "troubleItems": stats.get_trouble_items(),
            "environment": YAMLExporter._export_environment(),
        }
        
        if grouped_export_settings:
            report["export"] = grouped_export_settings
        
        # Generate filename with timestamp
        filename = f"review_session_{timestamp.strftime('%Y%m%d_%H%M%S')}.yaml"
        filepath = os.path.join(output_dir, filename)
        
        # Write YAML file
        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.safe_dump(report, f, default_flow_style=False, allow_unicode=True, sort_keys=True)
        
        return filepath
    
    @staticmethod
    def _export_settings(state: ReviewSessionState) -> Dict[str, Any]:
        """Export session settings."""
        return {
            "scope": state.scope,
            "playCountPerItem": state.playCountPerItem,
            "timeWeightingPercent": state.timeWeightingPercent,
            "perItemTimeLimitSec": state.perItemTimeLimitSec,
            "limitMode": state.limitMode,
            "uiOverheadMs": state.uiOverheadMs,
            "sfxEnabled": state.sfxEnabled,
            "sfxVolumePercent": state.sfxVolumePercent,
            "sfxTone": state.sfxTone,
            "quickConfirmMode": state.quickConfirmMode,
            "gradingThresholds": {
                "A+": 0.95,
                "A": 0.90,
                "B+": 0.80,
                "B": 0.75,
                "C+": 0.70,
                "C": 0.65,
                "D": 0.55,
            },
        }
    
    @staticmethod
    def _export_items(items: List[ItemStats]) -> List[Dict[str, Any]]:
        """Export per-item statistics."""
        result = []
        for item in items:
            result.append({
                "id": item.item_id,
                "type": item.media_type,
                "label": os.path.basename(item.media_path),
                "mediaPath": item.media_path,
                "wavPath": item.wav_path,
                "wrongGuesses": item.wrong_guesses,
                "timeToCorrectSec": round(item.time_to_correct_sec, 2),
                "overtime": item.overtime,
                "timeout": item.timeout,
                "attempts": item.attempts,
                "playCountServed": item.play_count_served,
                "confirmMethod": item.confirm_method,
                "notes": item.notes,
            })
        return result
    
    @staticmethod
    def _export_environment() -> Dict[str, Any]:
        """Export environment information."""
        env = {
            "os": os.name,
            "platform": platform.system(),
            "pythonVersion": sys.version.split()[0],
        }
        
        # Try to get ffmpeg/ffprobe paths
        try:
            from vat.utils.resources import resolve_ff_tools
            ff_tools = resolve_ff_tools()
            env["ffmpegPath"] = ff_tools.get("ffmpeg", "not found")
            env["ffprobePath"] = ff_tools.get("ffprobe", "not found")
        except Exception:
            env["ffmpegPath"] = "not found"
            env["ffprobePath"] = "not found"
        
        return env
