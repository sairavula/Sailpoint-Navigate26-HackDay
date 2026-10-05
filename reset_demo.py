#!/usr/bin/env python3
"""
Reset the rogue-agent demo to its starting state (run before every rehearsal and the live demo).

  - Re-enables invoice-bot's account on the ISC "Bots" source
  - Re-enables invoice-bot's account in the target app (SaaS demo API)
  - Prints the current state of both so you can confirm "ACTIVE / ACTIVE" before going on stage

Usage:
  python reset_demo.py            # show state only
  python reset_demo.py --apply    # re-enable both, then show state
"""

import asyncio
import sys

import governance
import target_app
from isc_client import ISCError, isc

AGENT = "invoice-bot"


async def _state() -> tuple[dict, dict]:
    agents, _ = await governance.load_agents()
    agent = next(a for a in agents if a["name"] == AGENT)
    isc_acct = (await isc.request("GET", f"/v3/accounts/{agent['accountId']}")).json()
    tgt = await target_app.find_account(AGENT)
    tags = (await isc.request("GET", f"/v3/tagged-objects/ACCOUNT/{agent['accountId']}")).json().get("tags") or []
    return {"accountId": agent["accountId"], "disabled": isc_acct.get("disabled"), "tags": tags}, (tgt or {})


async def main(apply: bool) -> int:
    isc_state, tgt = await _state()
    if apply:
        if isc_state["disabled"]:
            await isc.request("POST", f"/v3/accounts/{isc_state['accountId']}/enable", json={"forceProvisioning": False})
            print("ISC: enable submitted")
        agents, _ = await governance.load_agents()
        removed = await governance.set_quarantine_tag(next(a for a in agents if a["name"] == AGENT), on=False)
        print("ISC: quarantine tag removed from", removed or "nothing (not tagged)")
        if tgt.get("id") and tgt.get("active") is False:
            await target_app.enable_account(tgt["id"])
            print("target app: enabled")
        await asyncio.sleep(3)
        isc_state, tgt = await _state()
    print(f"ISC Bots account  {isc_state['accountId']}: {'DISABLED' if isc_state['disabled'] else 'ACTIVE'} tags={isc_state['tags']}")
    print(f"target app        {tgt.get('id')}: {'ACTIVE' if tgt.get('active') else 'DISABLED' if tgt else 'MISSING'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main("--apply" in sys.argv)))
    except (ISCError, target_app.TargetAppError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
