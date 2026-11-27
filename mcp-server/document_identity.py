"""活动文档目标的显式绑定与核验；不负责读取 COM 或批准用户操作。

PID 与规范化的已保存文档路径用于定位执行目标，并不证明文档内容没有变化，
也不构成对同系统用户进程的安全隔离。调用方必须在 CAD 操作锁内取得真实
PID 和活动文档路径，验证后使用同一个模型对象执行操作。
"""
from __future__ import annotations

import contextvars
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


class DocumentIdentityError(ValueError):
    """目标无效、未绑定或与实际活动文档不一致。"""


def _path(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\x00" in value:
        raise DocumentIdentityError("Document path must be a valid non-empty absolute path.")
    if any(character in value for character in ("*", "?")):
        raise DocumentIdentityError("Document path must not contain wildcards.")
    candidate = Path(value)
    if not candidate.is_absolute():
        raise DocumentIdentityError("Document path must be an absolute path; unsaved documents cannot use this verification.")
    if candidate.suffix.lower() not in {".sldprt", ".sldasm", ".slddrw"}:
        raise DocumentIdentityError("Target must be a saved native SolidWorks document path.")
    try:
        return os.path.normcase(str(candidate.resolve(strict=False)))
    except (OSError, RuntimeError, ValueError) as exc:
        raise DocumentIdentityError("Document path could not be normalized.") from exc


def _pid(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DocumentIdentityError("SolidWorks process ID must be a positive integer.")
    return value


@dataclass(frozen=True)
class DocumentIdentity:
    """审批绑定的 SolidWorks 进程及已保存文档路径。"""

    process_id: int
    path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "process_id", _pid(self.process_id))
        object.__setattr__(self, "path", _path(self.path))

    @classmethod
    def create(cls, process_id: object, path: object) -> DocumentIdentity:
        return cls(process_id, path)  # type: ignore[arg-type]

    def verify(self, process_id: object, path: object) -> None:
        """核对实际活动文档；调用方应在执行锁内立即使用已取回的模型对象。"""
        if _pid(process_id) != self.process_id:
            raise DocumentIdentityError("SolidWorks process does not match the approved target.")
        if _path(path) != self.path:
            raise DocumentIdentityError("Active document does not match the approved target.")


_target: contextvars.ContextVar[DocumentIdentity | None] = contextvars.ContextVar(
    "solidworks_approved_document_identity", default=None
)


@contextmanager
def bind_document(identity: DocumentIdentity) -> Iterator[None]:
    """把经批准的目标绑定到本次调用上下文，退出时恢复上层上下文。"""
    if not isinstance(identity, DocumentIdentity):
        raise DocumentIdentityError("Missing valid approved document identity.")
    token = _target.set(identity)
    try:
        yield
    finally:
        _target.reset(token)


def verify_bound_document(process_id: object, path: object) -> None:
    """验证当前调用所绑定的目标；缺少绑定时失败关闭。"""
    identity = _target.get()
    if identity is None:
        raise DocumentIdentityError("This call has no bound approved document identity.")
    identity.verify(process_id, path)


def has_bound_document() -> bool:
    """兼容完整模式：仅在服务端审批调用中强制执行目标核验。"""
    return _target.get() is not None
