"""Grouped export functionality for review sessions."""

import os
import shutil
from typing import List, Tuple, Optional, Dict, Any
import zipfile
from pathlib import Path


class GroupedExporter:
    """Exports recorded items into grouped folders.
    
    Supports two modes:
    1. Items per folder: split into groups of N items each
    2. Number of folders: split into M folders with equal distribution
    
    Each group folder contains:
    - Media files (images/videos)
    - Matching WAV files
    """
    
    @staticmethod
    def export_groups(
        items: List[Tuple[str, str]],  # (media_path, wav_path)
        output_dir: str,
        mode: str = "items_per_folder",
        value: int = 12,
        copy_or_move: str = "copy",
    ) -> Dict[str, Any]:
        """Export items into grouped folders.
        
        Args:
            items: List of (media_path, wav_path) tuples
            output_dir: Base directory for output
            mode: "items_per_folder" or "number_of_folders"
            value: Number of items per folder or number of folders
            copy_or_move: "copy" or "move" (default: copy)
        
        Returns:
            Dictionary with export metadata
        """
        if not items:
            return {
                "groupedMode": mode,
                "totalItems": 0,
                "totalGroups": 0,
                "copyOrMove": copy_or_move,
            }
        
        # Calculate grouping
        total_items = len(items)
        
        if mode == "items_per_folder":
            items_per_folder = max(1, value)
            num_groups = (total_items + items_per_folder - 1) // items_per_folder
        else:  # number_of_folders
            num_groups = max(1, min(value, total_items))
            items_per_folder = total_items // num_groups
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Split items into groups
        groups = []
        for i in range(num_groups):
            start_idx = i * items_per_folder
            if mode == "items_per_folder":
                end_idx = min(start_idx + items_per_folder, total_items)
            else:
                # Distribute remainder across groups
                if i < num_groups - 1:
                    end_idx = start_idx + items_per_folder
                else:
                    end_idx = total_items
            
            groups.append(items[start_idx:end_idx])
        
        # Export each group
        for i, group in enumerate(groups, start=1):
            group_name = f"Group {i:02d}"
            group_dir = os.path.join(output_dir, group_name)
            os.makedirs(group_dir, exist_ok=True)
            
            for media_path, wav_path in group:
                # Copy/move media file
                media_filename = os.path.basename(media_path)
                media_dest = os.path.join(group_dir, media_filename)
                if copy_or_move == "copy":
                    shutil.copy2(media_path, media_dest)
                else:
                    shutil.move(media_path, media_dest)
                
                # Copy/move WAV file
                if os.path.exists(wav_path):
                    wav_filename = os.path.basename(wav_path)
                    wav_dest = os.path.join(group_dir, wav_filename)
                    if copy_or_move == "copy":
                        shutil.copy2(wav_path, wav_dest)
                    else:
                        shutil.move(wav_path, wav_dest)
        
        # Calculate remainder (items in last folder)
        remainder = 0
        if mode == "items_per_folder" and groups:
            remainder = len(groups[-1])
        
        return {
            "groupedMode": mode,
            f"{'itemsPerFolder' if mode == 'items_per_folder' else 'numberOfFolders'}": value,
            "totalItems": total_items,
            "totalGroups": num_groups,
            "copyOrMove": copy_or_move,
            "remainderInLastFolder": remainder,
        }

    @staticmethod
    def export_sessions(
        sessions: List[List[Tuple[str, str]]],  # [[(media_path, wav_path), ...], ...]
        output_dir: str,
        export_format: str = "folders",  # "folders" or "zip"
        copy_or_move: str = "copy",
        group_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Export predefined sessions into folders or zip files.

        Args:
            sessions: List of sessions; each session is a list of (media_path, wav_path)
            output_dir: Destination directory
            export_format: "folders" to create Set NN directories, "zip" to create Set NN.zip archives
            copy_or_move: Only applies to folder export; "copy" or "move"
            group_names: Optional list of names to use per session; if provided, length should match sessions. Missing or empty names fall back to "Set N".

        Returns:
            Dictionary with export metadata
        """
        os.makedirs(output_dir, exist_ok=True)
        total_items = sum(len(s) for s in sessions)
        meta_groups: List[Dict[str, Any]] = []

        def _sanitize_name(name: str, default: str) -> str:
            # Replace filesystem-problematic characters and trim
            safe = (name or "").strip()
            if not safe:
                return default
            # Replace common invalids on Windows/macOS
            for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
                safe = safe.replace(ch, '-')
            # Avoid leading/trailing dots or spaces
            safe = safe.strip(' .')
            return safe or default

        for i, session in enumerate(sessions, start=1):
            suggested = None
            if group_names and i-1 < len(group_names):
                suggested = group_names[i-1]
            group_name = _sanitize_name(suggested or "", f"Set {i}")
            if export_format == "zip":
                zip_path = os.path.join(output_dir, f"{group_name}.zip")
                with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for media_path, wav_path in session:
                        if os.path.exists(media_path):
                            zf.write(media_path, arcname=os.path.basename(media_path))
                        if wav_path and os.path.exists(wav_path):
                            zf.write(wav_path, arcname=os.path.basename(wav_path))
                meta_groups.append({"name": group_name, "path": zip_path, "count": len(session)})
            else:
                group_dir = os.path.join(output_dir, group_name)
                os.makedirs(group_dir, exist_ok=True)
                for media_path, wav_path in session:
                    # Media file
                    if os.path.exists(media_path):
                        dest = os.path.join(group_dir, os.path.basename(media_path))
                        if copy_or_move == "copy":
                            shutil.copy2(media_path, dest)
                        else:
                            shutil.move(media_path, dest)
                    # WAV
                    if wav_path and os.path.exists(wav_path):
                        dest_wav = os.path.join(group_dir, os.path.basename(wav_path))
                        if copy_or_move == "copy":
                            shutil.copy2(wav_path, dest_wav)
                        else:
                            shutil.move(wav_path, dest_wav)
                meta_groups.append({"name": group_name, "path": group_dir, "count": len(session)})

        return {
            "format": export_format,
            "totalGroups": len(sessions),
            "totalItems": total_items,
            "groups": meta_groups,
        }
    
    @staticmethod
    def preview_groups(
        items: List[Tuple[str, str]],
        mode: str = "items_per_folder",
        value: int = 12,
    ) -> List[List[str]]:
        """Preview how items would be grouped without actually exporting.
        
        Args:
            items: List of (media_path, wav_path) tuples
            mode: "items_per_folder" or "number_of_folders"
            value: Number of items per folder or number of folders
        
        Returns:
            List of groups, where each group is a list of media filenames
        """
        if not items:
            return []
        
        total_items = len(items)
        
        if mode == "items_per_folder":
            items_per_folder = max(1, value)
            num_groups = (total_items + items_per_folder - 1) // items_per_folder
        else:  # number_of_folders
            num_groups = max(1, min(value, total_items))
            items_per_folder = total_items // num_groups
        
        groups = []
        for i in range(num_groups):
            start_idx = i * items_per_folder
            if mode == "items_per_folder":
                end_idx = min(start_idx + items_per_folder, total_items)
            else:
                # Distribute remainder across groups
                if i < num_groups - 1:
                    end_idx = start_idx + items_per_folder
                else:
                    end_idx = total_items
            
            group_items = [os.path.basename(media) for media, _ in items[start_idx:end_idx]]
            groups.append(group_items)
        
        return groups
