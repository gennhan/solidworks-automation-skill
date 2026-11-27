"""人工批准 SolidWorks MCP 的写操作。

用法::

    python scripts/sw_mcp_approve.py list
    python scripts/sw_mcp_approve.py approve 1a2b3c4d
    python scripts/sw_mcp_approve.py deny 1a2b3c4d

MCP 调用参数中的 ``approved=true`` 不会产生批准记录。交互式终端检查只防止
普通管道误操作，不能证明输入来自真人；能以同一操作系统用户运行代码的进程
可以访问本地账本或模拟终端，本机制不能隔离此类进程。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-server"))

from approval import ApprovalError, ApprovalLedger, default_root  # noqa: E402


def _format_time(timestamp: float | None) -> str:
    if not timestamp:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def _show_list(ledger: ApprovalLedger) -> int:
    print(f"Approval ledger directory: {ledger.root}")
    pending = ledger.pending()
    if pending:
        print("\nPending approvals:")
        for item in pending:
            remaining = max(0, int(item["expires_at"] - time.time()) // 60)
            print(f"  [{item['id']}] {item['tool']} ({item['effect']}, {remaining} min left)")
            print(f"        Args: {item['summary'][:300]}")
            if item.get("targets"):
                print(f"        Targets: {', '.join(item['targets'])}")
    else:
        print("\nPending approvals: none")

    decisions = ledger.decisions(5)
    if decisions:
        print("\nRecent decisions:")
        for item in decisions:
            print(f"  [{item['id']}] {item['status']} {item['tool']} @ {_format_time(item.get('decided_at'))}")
    return 0


def _confirm(prompt: str) -> bool:
    """要求交互式输入；TTY 本身不证明输入来自真人。"""
    if not sys.stdin.isatty():
        print("Denied: approval must be completed interactively in a terminal (stdin is not a TTY).", file=sys.stderr)
        return False
    try:
        answer = input(f"{prompt} Type 'yes' to confirm: ")
    except (EOFError, KeyboardInterrupt):
        # Windows 的 NUL 设备也会让 isatty() 返回真，必须兜住读不到输入的情况。
        print("\nDenied: no human confirmation received.", file=sys.stderr)
        return False
    return answer.strip().lower() == "yes"


def _show_request(ledger: ApprovalLedger, request_id: str) -> dict:
    record = ledger.request_record(request_id)
    print(f"Tool: {record['tool']}  Effect: {record['effect']}  Request: {request_id}")
    print(f"Args: {record['summary']}")
    if record.get("targets"):
        print(f"Targets: {', '.join(record['targets'])}")
    return record


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Manually approve SolidWorks MCP write operations")
    parser.add_argument("--dir", default=None, help="Approval ledger directory (defaults to SW_MCP_APPROVAL_DIR)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List pending approval requests and recent decisions")

    approve = sub.add_parser("approve", help="Approve a pending request")
    approve.add_argument("request_id")
    approve.add_argument("--ttl", type=int, default=None, help="Approval lifetime in seconds")

    deny = sub.add_parser("deny", help="Deny a pending request")
    deny.add_argument("request_id")

    scope = sub.add_parser("scope", help="Scoped grants are disabled (kept for CLI compatibility)")
    scope.add_argument("--tool", action="append", required=True, help="Tool name (repeatable; * for all write tools)")
    scope.add_argument("--path", action="append", default=[], help="Allowed directory prefix (repeatable; omit for unrestricted)")
    scope.add_argument("--ttl", type=int, default=None, help="Lifetime in seconds")
    scope.add_argument("--uses", type=int, default=None, help="Maximum number of uses; omit for unlimited")

    args = parser.parse_args(argv)
    ledger = ApprovalLedger(args.dir or default_root())
    command = args.command or "list"

    try:
        if command == "list":
            return _show_list(ledger)
        if command == "approve":
            record = _show_request(ledger, args.request_id)
            if not _confirm(f"Approve this call to {record['tool']}?"):
                return 1
            grant = ledger.approve(args.request_id, args.ttl, expected_record=record)
            print(f"Approved until {_format_time(grant['expires_at'])} (valid for this call only).")
            return 0
        if command == "deny":
            _show_request(ledger, args.request_id)
            if not _confirm("Deny this call?"):
                return 1
            ledger.deny(args.request_id)
            print("Denied.")
            return 0
        if command == "scope":
            raise ApprovalError("Scoped grants are disabled; review and approve each call individually.")
    except ApprovalError as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1
    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
