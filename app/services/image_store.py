from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class ImageStore(ABC):
    @abstractmethod
    def save(self, local_path: Path, dest_path: Path) -> str:
        """Save a local file to the store at dest_path and return a public URL."""
        raise NotImplementedError


class LocalImageStore(ImageStore):
    def __init__(self, base_dir: Path, base_url: str = "/assets"):
        self.base_dir = Path(base_dir)
        self.base_url = base_url.rstrip("/")

    def save(self, local_path: Path, dest_path: Path) -> str:
        local_path = Path(local_path)
        dest = self.base_dir / dest_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        rel = dest.relative_to(self.base_dir)
        return f"{self.base_url}/{rel.as_posix()}"

