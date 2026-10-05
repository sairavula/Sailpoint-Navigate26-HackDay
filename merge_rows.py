#!/usr/bin/env python3
"""
Enable row merging on the "Bots" delimited-file source.

ai-agents.csv has one row per (bot, entitlement). Without merging, aggregation keeps
a single row per account id and invoice-bot loses one of its two entitlements, so
the AccountsPayable / AccountsReceivable SoD conflict disappears.

Sets connectorAttributes: mergeRows=true, indexColumns=["id"], mergeColumns=["groups"].

Usage:
  python merge_rows.py                 # show current settings (read-only)
  python merge_rows.py --apply         # patch the source, then read it back
  python merge_rows.py --source NAME   # target a source other than "Bots"
"""

import asyncio
import json
import sys

from isc_client import ISCError, isc, quote

WANTED = {"mergeRows": True, "indexColumns": ["id"], "mergeColumns": ["groups"]}


def _arg(flag: str, default: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


async def main() -> int:
    name = _arg("--source", "Bots")
    sources = await isc.list_all("/v3/sources", params={"filters": f'name eq "{quote(name)}"'})
    if not sources:
        print(f"ERROR: source '{name}' not found")
        return 1
    src = sources[0]
    ca = src.get("connectorAttributes") or {}
    print(f"source={src['name']} id={src['id']} connector={src.get('connectorName') or src.get('type')}")
    print("current:", json.dumps({k: ca.get(k) for k in WANTED}))

    if "--apply" not in sys.argv:
        print("dry run: re-run with --apply to set", json.dumps(WANTED))
        return 0

    ops = [{"op": "add", "path": f"/connectorAttributes/{k}", "value": v} for k, v in WANTED.items()]
    await isc.request(
        "PATCH", f"/v3/sources/{src['id']}", json=ops,
        headers={"Content-Type": "application/json-patch+json"},
    )
    after = (await isc.request("GET", f"/v3/sources/{src['id']}")).json().get("connectorAttributes") or {}
    print("after:  ", json.dumps({k: after.get(k) for k in WANTED}))
    ok = all(after.get(k) == v for k, v in WANTED.items())
    print("OK: merge enabled. Re-run account aggregation (upload ai-agents.csv again)." if ok else "WARN: values did not persist")
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except ISCError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
