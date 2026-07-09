from pathlib import Path


class FileCachedLoader:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._mtime_ns: int | None = None
        self._content: str | None = None

    def load(self) -> str:
        stat = self.path.stat()

        if self._content is not None and self._mtime_ns == stat.st_mtime_ns:
            return self._content

        content = self.path.read_text(encoding="utf-8")
        if not content.strip():
            msg = f"{self.path} is empty"
            raise ValueError(msg)

        self._mtime_ns = stat.st_mtime_ns
        self._content = content
        return content
