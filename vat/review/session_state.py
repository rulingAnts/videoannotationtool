"""Review session state management."""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ReviewSessionState:
    """Manages review session settings and transient state.
    
    Settings (persisted):
    - scope: "images", "videos", or "both"
    - playCountPerItem: number of times each item is presented
    - perItemTimeLimitSec: time limit per item (0 = no limit)
    - limitMode: "soft" or "hard"
    - timeWeightingPercent: 0-100, weight of time in composite grade
    - uiOverheadMs: baseline UI overhead to subtract from timing
    - sfxEnabled: sound effects on/off
    - sfxVolumePercent: 0-100, sound effect volume
    - sfxTone: "default" or "gentle"
    - quickConfirmMode: enable quick confirm (right-click, Ctrl/Cmd+Click)
    - groupedDefaultItemsPerFolder: default items per folder for grouped export
    
    Transient state (not persisted):
    - sessionActive: whether a session is currently running
    - paused: whether the session is paused
    - currentPromptIndex: index in the queue
    """
    
    # Persisted settings
    scope: str = "both"
    playCountPerItem: int = 1
    perItemTimeLimitSec: float = 0.0
    limitMode: str = "soft"
    timeWeightingPercent: int = 20
    uiOverheadMs: int = 2000
    sfxEnabled: bool = True
    sfxVolumePercent: int = 70
    sfxTone: str = "default"
    quickConfirmMode: bool = True
    groupedDefaultItemsPerFolder: int = 12
    reviewThumbScale: float = 1.0
    
    # Transient state
    sessionActive: bool = False
    paused: bool = False
    currentPromptIndex: int = 0
    
    @classmethod
    def get_default_settings(cls) -> Dict[str, Any]:
        """Return default settings as a dictionary."""
        defaults = cls()
        return {
            "scope": defaults.scope,
            "playCountPerItem": defaults.playCountPerItem,
            "perItemTimeLimitSec": defaults.perItemTimeLimitSec,
            "limitMode": defaults.limitMode,
            "timeWeightingPercent": defaults.timeWeightingPercent,
            "uiOverheadMs": defaults.uiOverheadMs,
            "sfxEnabled": defaults.sfxEnabled,
            "sfxVolumePercent": defaults.sfxVolumePercent,
            "sfxTone": defaults.sfxTone,
            "quickConfirmMode": defaults.quickConfirmMode,
            "groupedDefaultItemsPerFolder": defaults.groupedDefaultItemsPerFolder,
            "reviewThumbScale": defaults.reviewThumbScale,
        }
    
    def load_from_json(self, settings: Dict[str, Any]) -> None:
        """Load settings from a dictionary (typically from JSON)."""
        review_settings = settings.get("review", {})
        
        self.scope = review_settings.get("scope", self.scope)
        self.playCountPerItem = review_settings.get("playCountPerItem", self.playCountPerItem)
        self.perItemTimeLimitSec = review_settings.get("perItemTimeLimitSec", self.perItemTimeLimitSec)
        self.limitMode = review_settings.get("limitMode", self.limitMode)
        self.timeWeightingPercent = review_settings.get("timeWeightingPercent", self.timeWeightingPercent)
        self.uiOverheadMs = review_settings.get("uiOverheadMs", self.uiOverheadMs)
        
        sfx = review_settings.get("sfx", {})
        self.sfxEnabled = sfx.get("enabled", self.sfxEnabled)
        self.sfxVolumePercent = sfx.get("volumePercent", self.sfxVolumePercent)
        self.sfxTone = sfx.get("tone", self.sfxTone)
        
        self.quickConfirmMode = review_settings.get("quickConfirmMode", self.quickConfirmMode)
        self.reviewThumbScale = review_settings.get("reviewThumbScale", self.reviewThumbScale)
        
        grouped = review_settings.get("grouped", {})
        self.groupedDefaultItemsPerFolder = grouped.get("defaultItemsPerFolder", self.groupedDefaultItemsPerFolder)
    
    def save_to_json(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Save settings to a dictionary (for JSON serialization).
        
        Args:
            settings: Existing settings dictionary to update
            
        Returns:
            Updated settings dictionary
        """
        if "review" not in settings:
            settings["review"] = {}
        
        settings["review"]["scope"] = self.scope
        settings["review"]["playCountPerItem"] = self.playCountPerItem
        settings["review"]["perItemTimeLimitSec"] = self.perItemTimeLimitSec
        settings["review"]["limitMode"] = self.limitMode
        settings["review"]["timeWeightingPercent"] = self.timeWeightingPercent
        settings["review"]["uiOverheadMs"] = self.uiOverheadMs
        settings["review"]["quickConfirmMode"] = self.quickConfirmMode
        settings["review"]["reviewThumbScale"] = float(self.reviewThumbScale)
        
        if "sfx" not in settings["review"]:
            settings["review"]["sfx"] = {}
        settings["review"]["sfx"]["enabled"] = self.sfxEnabled
        settings["review"]["sfx"]["volumePercent"] = self.sfxVolumePercent
        settings["review"]["sfx"]["tone"] = self.sfxTone
        
        if "grouped" not in settings["review"]:
            settings["review"]["grouped"] = {}
        settings["review"]["grouped"]["defaultItemsPerFolder"] = self.groupedDefaultItemsPerFolder
        
        return settings
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""
        defaults = self.get_default_settings()
        self.scope = defaults["scope"]
        self.playCountPerItem = defaults["playCountPerItem"]
        self.perItemTimeLimitSec = defaults["perItemTimeLimitSec"]
        self.limitMode = defaults["limitMode"]
        self.timeWeightingPercent = defaults["timeWeightingPercent"]
        self.uiOverheadMs = defaults["uiOverheadMs"]
        self.sfxEnabled = defaults["sfxEnabled"]
        self.sfxVolumePercent = defaults["sfxVolumePercent"]
        self.sfxTone = defaults["sfxTone"]
        self.quickConfirmMode = defaults["quickConfirmMode"]
        self.groupedDefaultItemsPerFolder = defaults["groupedDefaultItemsPerFolder"]
    
    def reset_session(self) -> None:
        """Reset transient session state."""
        self.sessionActive = False
        self.paused = False
        self.currentPromptIndex = 0
