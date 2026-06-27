"""Compare two {relpath: hash} mappings and report differences."""

from dataclasses import dataclass, field


@dataclass
class DiffResult:
    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.modified)


class Differ:
    """Static diff between two file-to-hash dicts."""

    @staticmethod
    def compare(source: dict[str, str], target: dict[str, str]) -> DiffResult:
        src_paths = set(source)
        tgt_paths = set(target)

        added = sorted(src_paths - tgt_paths)
        removed = sorted(tgt_paths - src_paths)
        modified = sorted(
            p for p in (src_paths & tgt_paths) if source[p] != target[p]
        )
        unchanged = sorted(
            p for p in (src_paths & tgt_paths) if source[p] == target[p]
        )

        return DiffResult(
            added=added,
            modified=modified,
            removed=removed,
            unchanged=unchanged,
        )
