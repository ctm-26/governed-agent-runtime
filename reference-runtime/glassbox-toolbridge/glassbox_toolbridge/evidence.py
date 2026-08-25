from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import EvidenceArtifact


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class AuditLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return "0" * 64
        return json.loads(lines[-1])["event_hash"]

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "event_type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "previous_hash": self._last_hash(),
            "payload": payload,
        }
        record["event_hash"] = sha256_bytes(canonical_json(record))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def verify(self) -> bool:
        previous = "0" * 64
        if not self.path.exists():
            return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            event_hash = record.pop("event_hash")
            if record["previous_hash"] != previous:
                return False
            if sha256_bytes(canonical_json(record)) != event_hash:
                return False
            previous = event_hash
        return True


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw_dir = root / "evidence" / "raw"
        self.normalized_dir = root / "evidence" / "normalized"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.normalized_dir.mkdir(parents=True, exist_ok=True)

    def write_json(
        self,
        *,
        kind: str,
        payload: dict[str, Any],
        source_connector: str,
        request_id: str,
        scope_token_id: str,
        raw: bool,
    ) -> EvidenceArtifact:
        data = canonical_json(payload)
        digest = sha256_bytes(data)
        artifact_id = f"ev-{digest[:16]}"
        directory = self.raw_dir if raw else self.normalized_dir
        path = directory / f"{artifact_id}.json"
        if path.exists() and path.read_bytes() != data:
            raise RuntimeError("immutable artifact collision")
        if not path.exists():
            path.write_bytes(data)
        return EvidenceArtifact(
            artifact_id=artifact_id,
            kind=kind,
            relative_path=path.relative_to(self.root).as_posix(),
            sha256=digest,
            created_at=datetime.now(timezone.utc),
            source_connector=source_connector,
            request_id=request_id,
            scope_token_id=scope_token_id,
            media_type="application/json",
        )
