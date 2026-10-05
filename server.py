#!/usr/bin/env python3
"""
"Green Isn't Safe": SailPoint Navigate Hack Day MCP server.

An identity governance agent that explains access and exposes what dashboards miss,
including AI agents whose accountability chain is broken.

Author: Sai Ravula, Alex, Muyiwa | CAI IAM & DP
Version: 2.0.0

Layout (one owner per file):
  isc_client.py  shared ISC client (auth, retry, pagination)
  explain.py     explain_access                                       (Alex)
  governance.py  find_accountability_gaps, detect_rogue_agents,
                 quarantine_agent                                      (Sai)
  target_app.py  the agent's target application (SaaS demo API)
  server.py      tool registration only

Security:
- Credentials from the OS credential store (macOS Keychain / Windows Credential Manager)
- Every tool read-only except quarantine_agent, which is dry-run unless confirm=true
- Splunk-ready key=value logging to ~/.sailpoint-hackday-mcp/server.log, secrets redacted
"""

import asyncio
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

import explain
import governance
from isc_client import BASE_URL, KEYCHAIN_SERVICE, ISCError, isc, lifecycle_state

mcp = FastMCP("sailpoint-hackday")

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
CONTAINMENT = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)


@mcp.tool(annotations=READ_ONLY)
async def search_identities(query: str, limit: int = 10) -> dict:
    """Search identities in the SailPoint demo tenant.

    Use when the user asks about a person (by name, email, department) or wants
    identities matching a condition. `query` is ISC search syntax, e.g.
    "Adam Kennedy", "attributes.department:Engineering", or "inactive:true".
    Returns compact identity summaries (lifecycle state, manager, access count).
    """
    if not query.strip():
        return {"error": "query must not be empty"}
    try:
        docs = await isc.search("identities", query.strip(), limit=max(1, min(limit, 100)))
    except ISCError as exc:
        return {"error": str(exc)}
    return {"count": len(docs), "identities": [
        {"id": d.get("id"), "name": d.get("name"), "email": d.get("email"),
         "lifecycleState": lifecycle_state(d), "manager": (d.get("manager") or {}).get("name"),
         "department": (d.get("attributes") or {}).get("department"), "accessCount": d.get("accessCount")}
        for d in docs]}


mcp.tool(annotations=READ_ONLY)(explain.explain_access)
mcp.tool(annotations=READ_ONLY)(governance.find_accountability_gaps)
mcp.tool(annotations=READ_ONLY)(governance.detect_rogue_agents)
mcp.tool(annotations=CONTAINMENT)(governance.quarantine_agent)


async def _selftest() -> None:
    print(f"base_url={BASE_URL} keychain_service={KEYCHAIN_SERVICE}")
    r = await search_identities("Adam Kennedy", limit=1)
    print("OK search_identities" if r.get("identities") else f"FAIL search_identities: {r}")
    r = await governance.detect_rogue_agents()
    print("OK detect_rogue_agents" if "agents" in r else f"FAIL detect_rogue_agents: {r}",
          [(a["agent"], a["riskScore"], a["severity"]) for a in r.get("agents", [])])
    r = await explain.explain_access("invoice-bot", "AccountsReceivable")
    print("OK explain_access" if r.get("holds") else f"FAIL explain_access: {r}", r.get("summary"))
    r = await governance.quarantine_agent("invoice-bot", reason="selftest dry run")
    print("OK quarantine_agent (dry run)" if r.get("mode") == "DRY_RUN" else f"FAIL quarantine_agent: {r}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        asyncio.run(_selftest())
    else:
        mcp.run()
