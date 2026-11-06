"""Media file storage under uploads/cx/…"""

from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from app.config.settings import get_settings


class MediaStore:
    """Copy originals and optional thumbnails onto disk."""

    def __init__(self, *, company_id: int, work_order_id: int) -> None:
        settings = get_settings()
        self._root = (
            Path(settings.uploads_dir)
            / "cx"
            / f"c{company_id}"
            / f"wo{work_order_id}"
        )
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def save_file(self, source: Path, *, prefix: str = "media") -> tuple[str, int, str]:
        """
        Copy *source* into the WO folder.

        Returns (relative_path_from_uploads, size, sha256_hex).
        """
        if not source.is_file():
            raise FileNotFoundError(str(source))
        ext = source.suffix.lower() or ".bin"
        name = f"{prefix}_{uuid.uuid4().hex}{ext}"
        dest = self._root / name
        shutil.copy2(source, dest)
        data = dest.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        settings = get_settings()
        rel = str(dest.relative_to(Path(settings.uploads_dir))).replace("\\", "/")
        return rel, len(data), digest

    def absolute(self, relative: str) -> Path:
        return Path(get_settings().uploads_dir) / relative
