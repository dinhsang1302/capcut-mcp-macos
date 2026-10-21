"""Load and persist a CapCut draft_content.json, with backups and write gating."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from . import paths

CONTENT = "draft_content.json"
BACKUP_DIR = ".mcp_backups"
MAX_BACKUPS = 40


class DraftError(RuntimeError):
    pass


class Draft:
    """One CapCut project, held as the parsed draft graph."""

    def __init__(self, folder: Path, data: dict):
        self.folder = folder
        self.data = data
        target = folder / CONTENT
        self._loaded_bytes = target.read_bytes() if target.exists() else None

    # ------------------------------------------------------------------ load

    @classmethod
    def open(cls, name_or_path: str, draft_root: Path | None = None) -> "Draft":
        folder = paths.resolve_project(name_or_path, draft_root)
        target = folder / CONTENT
        try:
            raw_bytes = target.read_bytes()
            raw = raw_bytes.decode('utf-8-sig')
        except OSError as exc:
            raise DraftError(f"Cannot read {target}: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise DraftError(
                f"{target} is not UTF-8 text. This CapCut build likely encrypts "
                f"drafts, so direct editing is unavailable: {exc}"
            ) from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DraftError(
                f"{target} is not valid JSON (encrypted or a newer schema): {exc}"
            ) from exc

        if not isinstance(data, dict) or not isinstance(data.get('tracks'), list) or not isinstance(data.get('materials'), dict):
            raise DraftError('Unrecognised draft structure. A real macOS sample must be verified before editing.')
        opened = cls(folder, data)
        opened._loaded_bytes = raw_bytes
        return opened

    # ----------------------------------------------------------------- write

    def save(self, *, force: bool = False, backup: bool = True) -> dict:
        """Write the draft back, refusing while CapCut holds the project open."""
        if force:
            raise DraftError('Force saving is disabled in the macOS edition.')
        if not backup:
            raise DraftError('Saving without a backup is disabled in the macOS edition.')
        pids = paths.running_pids()
        if pids:
            raise DraftError(
                f"CapCut is running (PIDs {pids}). It flushes its own copy of the "
                "project on close. Quit CapCut normally before saving."
            )

        target = self.folder / CONTENT
        if not target.is_file() or target.read_bytes() != self._loaded_bytes:
            raise DraftError('Draft changed since it was loaded. Discard/reload and review before saving.')
        backup_path = None
        if backup and target.exists():
            backup_path = self._backup(target)

        # CapCut writes compact JSON; matching that keeps diffs and file size
        # comparable to what the app itself produces.
        payload = json.dumps(self.data, ensure_ascii=False, separators=(",", ":"))

        tmp = target.with_suffix(".json.mcp-tmp")
        tmp.write_text(payload, encoding="utf-8", newline="")
        try:
            if paths.running_pids() or target.read_bytes() != self._loaded_bytes:
                raise DraftError('CapCut started or draft changed before write; save cancelled.')
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
        self._loaded_bytes = target.read_bytes()

        return {
            "saved": str(target),
            "bytes": len(payload.encode("utf-8")),
            "backup": str(backup_path) if backup_path else None,
            "capcut_was_running": bool(pids),
        }

    def _backup(self, target: Path) -> Path:
        d = self.folder / BACKUP_DIR
        d.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S") + f'-{time.time_ns() % 1_000_000_000:09d}'
        dest = d / f"draft_content.{stamp}.json"
        shutil.copy2(target, dest)

        keep = sorted(d.glob("draft_content.*.json"), reverse=True)[:MAX_BACKUPS]
        for old in sorted(d.glob("draft_content.*.json"), reverse=True)[MAX_BACKUPS:]:
            if old not in keep:
                old.unlink(missing_ok=True)
        return dest

    def restore(self, backup_name: str | None = None) -> dict:
        """Roll back to a backup -- newest one unless a filename is given."""
        d = self.folder / BACKUP_DIR
        available = sorted(d.glob("draft_content.*.json"), reverse=True)
        if not available:
            raise DraftError(f"No backups in {d}")

        src = next((b for b in available if b.name == backup_name), None) if backup_name else available[0]
        if src is None:
            raise DraftError(f"No backup named '{backup_name}' in {d}")

        pids = paths.running_pids()
        if pids:
            raise DraftError(f"Close CapCut before restoring (PIDs {pids}).")

        shutil.copy2(src, self.folder / CONTENT)
        self.data = json.loads((self.folder / CONTENT).read_text(encoding="utf-8"))
        self._loaded_bytes = (self.folder / CONTENT).read_bytes()
        return {"restored_from": str(src)}

    def backups(self) -> list[str]:
        d = self.folder / BACKUP_DIR
        try:
            return [p.name for p in sorted(d.glob("draft_content.*.json"), reverse=True)]
        except OSError:
            return []
