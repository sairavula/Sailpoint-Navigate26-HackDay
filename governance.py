"""
Governance tools: Expose (accountability gaps), Detect (rogue agents), Contain (quarantine).

Root cause these tools target: accountability is a property of a chain
(identity -> access -> owner -> owner's manager -> lifecycle), but ISC is viewed
one object at a time. Each tool walks the chain and returns evidence[] records
(ids + timestamps) so every claim is replayable by an auditor.
"""

import asyncio
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import target_app
from isc_client import EXPERIMENTAL, ISCError, is_inactive, isc, lifecycle_state, logger

REGISTRY_FILE = Path(__file__).with_name("agents.json")
BOTS_SOURCE_NAME = os.getenv("BOTS_SOURCE_NAME", "Bots")
FALLBACK_GOVERNANCE_OWNER = os.getenv("GOVERNANCE_FALLBACK_OWNER", "hack.day")

# Keyword heuristic for "sensitive" access that the tenant doesn't flag as privileged.
SENSITIVE = re.compile(r"prod|vpn|treasury|admin|payable|receivable|payroll", re.IGNORECASE)

RISK_WEIGHTS = {
    "ORPHANED_OWNER": 40,
    "SOD_CONFLICT": 30,
    "PURPOSE_DRIFT": 20,
    "OWNER_NO_MANAGER": 10,
    "PRIVILEGED_DIRECT": 10,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ev(kind: str, obj_id: Optional[str], name: Optional[str], detail: str) -> dict:
    return {"type": kind, "id": obj_id, "name": name, "detail": detail}


def severity(score: int) -> str:
    return "CRITICAL" if score >= 70 else "HIGH" if score >= 40 else "MEDIUM" if score >= 20 else "LOW"


# =============================================================================
# Agent registry adapter: ISC machine identities first, local file fallback
# =============================================================================


async def load_agents() -> tuple[list[dict], str]:
    try:
        items = await isc.list_all("/machine-identities/v2", headers=EXPERIMENTAL, params={"filters": 'subtype eq "AI_AGENT"'})
    except ISCError:
        items = []
    if items:
        agents = [
            {
                "id": m.get("id"),
                "name": m.get("name") or m.get("nativeIdentity"),
                "subtype": m.get("subtype"),
                "description": m.get("description"),
                "owner": ((m.get("owners") or {}).get("primary") or {}).get("name"),
                "declaredAccess": (m.get("attributes") or {}).get("declaredAccess", []),
                "entitlements": [e.get("displayName") for e in m.get("userEntitlements") or [] if e.get("displayName")],
                "targetAccount": (m.get("attributes") or {}).get("targetAccount"),
                "status": m.get("status") or "ACTIVE",
            }
            for m in items
        ]
        return agents, "isc:/machine-identities/v2"

    bots = await _agents_from_source(BOTS_SOURCE_NAME)
    if bots:
        return bots, f"isc:source:{BOTS_SOURCE_NAME}"

    data = json.loads(REGISTRY_FILE.read_text())
    return data["agents"], "local:agents.json"


def _as_list(v) -> list[str]:
    if v is None or v == "":
        return []
    return [x for x in (v if isinstance(v, list) else str(v).split(";")) if x]


async def _agents_from_source(source_name: str) -> list[dict]:
    """Agents aggregated from a delimited-file source (one account per agent)."""
    try:
        srcs = await isc.list_all("/v3/sources", params={"filters": f'name eq "{source_name}"'})
        if not srcs:
            return []
        src = srcs[0]
        accounts = await isc.list_all("/v3/accounts", params={"filters": f'sourceId eq "{src["id"]}"'})
    except ISCError:
        return []
    tag_docs = await asyncio.gather(*(isc.request("GET", f"/v3/tagged-objects/ACCOUNT/{a['id']}") for a in accounts))
    quarantined = {a["id"] for a, t in zip(accounts, tag_docs) if QUARANTINE_TAG in (t.json().get("tags") or [])}
    agents = []
    for a in accounts:
        attrs = a.get("attributes") or {}
        agents.append({
            "id": a.get("id"),
            "accountId": a.get("id"),
            "identityId": a.get("identityId"),
            "sourceId": src["id"],
            "sourceName": src["name"],
            "name": attrs.get("name") or a.get("name"),
            "subtype": attrs.get("type", "AI_AGENT"),
            "description": attrs.get("description"),
            "owner": attrs.get("owner"),
            "declaredAccess": _as_list(attrs.get("declaredAccess")),
            "entitlements": _as_list(attrs.get("groups")),
            "targetAccount": attrs.get("targetAccount") or attrs.get("name"),
            "status": "QUARANTINED" if a.get("id") in quarantined else "DISABLED" if a.get("disabled") else (attrs.get("status") or "ACTIVE"),
            "aggregated": a.get("modified"),
        })
    return agents


QUARANTINE_TAG = "AGENT_QUARANTINED"


async def set_quarantine_tag(agent: dict, on: bool) -> list[str]:
    """Add/remove the quarantine tag on the agent's ISC account and identity. Returns objects changed."""
    changed = []
    for obj_type, obj_id in (("ACCOUNT", agent.get("accountId")), ("IDENTITY", agent.get("identityId"))):
        if not obj_id:
            continue
        current = (await isc.request("GET", f"/v3/tagged-objects/{obj_type}/{obj_id}")).json().get("tags") or []
        tags = sorted(set(current) | {QUARANTINE_TAG}) if on else [t for t in current if t != QUARANTINE_TAG]
        if tags != current:
            await isc.request("PUT", f"/v3/tagged-objects/{obj_type}/{obj_id}",
                              json={"objectRef": {"type": obj_type, "id": obj_id}, "tags": tags})
            changed.append(f"{obj_type}:{obj_id}")
    return changed


def _registry_kind(registry: str) -> str:
    if registry.startswith("isc:/machine-identities"):
        return "machine"
    if registry.startswith("isc:source:"):
        return "source"
    return "local"


def _save_local_status(agent_name: str, status: str, reason: str) -> None:
    data = json.loads(REGISTRY_FILE.read_text())
    for a in data["agents"]:
        if a["name"] == agent_name:
            a["status"] = status
            a.setdefault("history", []).append({"at": _now(), "status": status, "reason": reason})
    REGISTRY_FILE.write_text(json.dumps(data, indent=2) + "\n")


# =============================================================================
# Shared lookups
# =============================================================================


async def _entitlements_by_name(names: list[str], source_id: Optional[str] = None) -> dict[str, dict]:
    """Resolve entitlement names to ISC entitlement docs (scoped to source_id when given)."""
    if not names:
        return {}
    if source_id:
        # Entitlements API, not search: the search index lags fresh aggregations,
        # and an unresolved id would silently degrade SoD matching to names.
        quoted = ", ".join(f'"{n}"' for n in sorted(set(names)))
        docs = await isc.list_all("/v2025/entitlements", params={"filters": f'source.id eq "{source_id}" and name in ({quoted})'})
    else:
        query = "name:(" + " OR ".join(f'"{n}"' for n in sorted(set(names))) + ")"
        docs = await isc.search("entitlements", query, limit=250)
    return {d["name"]: d for d in docs if d.get("name") in names}


async def _sod_pairs() -> list[dict]:
    """Conflicting-access SoD policies as {name, id, left:set, right:set}."""
    pairs = []
    for p in await isc.list_all("/v3/sod-policies"):
        crit = p.get("conflictingAccessCriteria") or {}
        lc = (crit.get("leftCriteria") or {}).get("criteriaList") or []
        rc = (crit.get("rightCriteria") or {}).get("criteriaList") or []
        if lc and rc:
            pairs.append({"name": p["name"], "id": p["id"], "state": p.get("state"),
                          "left": {c.get("name") for c in lc}, "right": {c.get("name") for c in rc},
                          "leftIds": {c.get("id") for c in lc}, "rightIds": {c.get("id") for c in rc}})
    return pairs


def sod_conflicts(held: dict[str, Optional[str]], pairs: list[dict]) -> list[dict]:
    """Match held entitlements {name: id} against SoD pairs.

    Matches on entitlement ID when the agent's entitlements resolved to ISC ids,
    so a policy on AD entitlements never fires for same-named entitlements on
    another source. Falls back to names only for unresolved (local) entitlements.
    """
    out = []
    for p in pairs:
        left = sorted(n for n, i in held.items() if ((i in p["leftIds"]) if i else (n in p["left"])))
        right = sorted(n for n, i in held.items() if ((i in p["rightIds"]) if i else (n in p["right"])))
        if left and right:
            out.append({"policy": p["name"], "policyId": p["id"], "left": left, "right": right,
                        "matchedOn": "id" if all(held[n] for n in left + right) else "name"})
    return out


async def _owner_chain(owner_name: Optional[str]) -> dict:
    """Owner -> status -> manager -> escalation target."""
    if not owner_name:
        return {"owner": None, "status": "NO_OWNER", "escalateTo": FALLBACK_GOVERNANCE_OWNER}
    doc = await isc.identity_by_name(owner_name)
    if not doc:
        return {"owner": owner_name, "status": "OWNER_NOT_FOUND", "escalateTo": FALLBACK_GOVERNANCE_OWNER}
    manager = (doc.get("manager") or {}).get("name")
    enabled = [(a.get("source") or {}).get("name") for a in doc.get("accounts") or [] if a.get("disabled") is False]
    return {
        "owner": doc["name"],
        "ownerId": doc["id"],
        "lifecycleState": lifecycle_state(doc),
        "status": "OWNER_INACTIVE" if is_inactive(doc) else "OK",
        "ownerEnabledAccounts": enabled,
        "manager": manager,
        "escalateTo": manager or FALLBACK_GOVERNANCE_OWNER,
        "modified": doc.get("modified"),
    }


# =============================================================================
# Pure scoring (unit-testable without network)
# =============================================================================


def score_agent(agent: dict, chain: dict, ents: dict[str, dict], conflicts: list[dict]) -> dict:
    held = set(agent.get("entitlements") or [])
    declared = set(agent.get("declaredAccess") or [])
    signals: list[dict] = []
    evidence: list[dict] = []

    if chain["status"] in ("OWNER_INACTIVE", "OWNER_NOT_FOUND", "NO_OWNER"):
        signals.append({"signal": "ORPHANED_OWNER", "detail": f"Owner {chain.get('owner')} is {chain['status']} (lifecycle={chain.get('lifecycleState')})"})
        evidence.append(_ev("IDENTITY", chain.get("ownerId"), chain.get("owner"),
                            f"lifecycle={chain.get('lifecycleState')} enabledAccounts={chain.get('ownerEnabledAccounts')} modified={chain.get('modified')}"))
    if chain.get("owner") and not chain.get("manager"):
        signals.append({"signal": "OWNER_NO_MANAGER", "detail": f"Owner {chain['owner']} has no manager; escalation falls back to {chain['escalateTo']}"})

    drift = sorted(held - declared)
    if drift:
        signals.append({"signal": "PURPOSE_DRIFT", "detail": f"Holds {drift} beyond declared purpose {sorted(declared)}"})

    for c in conflicts:
        signals.append({"signal": "SOD_CONFLICT", "detail": f"Violates '{c['policy']}': {c['left']} vs {c['right']}"})
        evidence.append(_ev("SOD_POLICY", c["policyId"], c["policy"], f"left={c['left']} right={c['right']}"))

    priv = sorted(n for n in held if (ents.get(n) or {}).get("privileged"))
    if priv:
        signals.append({"signal": "PRIVILEGED_DIRECT", "detail": f"Privileged entitlements granted directly (no role/access profile): {priv}"})
    for n in sorted(held):
        e = ents.get(n) or {}
        evidence.append(_ev("ENTITLEMENT", e.get("id"), n, f"source={(e.get('source') or {}).get('name')} privileged={e.get('privileged')}"))

    score = min(100, sum(RISK_WEIGHTS[s["signal"]] for s in {s["signal"]: s for s in signals}.values()))
    return {
        "agent": agent["name"],
        "registryStatus": agent.get("status"),
        "riskScore": score,
        "severity": severity(score),
        "rogue": score >= 70,
        "signals": signals,
        "ownerChain": chain,
        "evidence": evidence,
    }


def bus_factor(objects: dict[str, list[dict]]) -> dict:
    owners = Counter((o.get("owner") or {}).get("name") for objs in objects.values() for o in objs)
    owners.pop(None, None)
    total = sum(len(v) for v in objects.values())
    top, top_n = (owners.most_common(1) or [(None, 0)])[0]
    return {"objects": total, "topOwner": top, "topOwnerObjects": top_n,
            "topOwnerShare": round(top_n / total, 2) if total else 0.0, "distinctOwners": len(owners)}


# =============================================================================
# Tools
# =============================================================================


async def find_accountability_gaps(max_items: int = 15) -> dict:
    """Is our governance actually healthy? Checks what point-in-time controls miss.

    Use when asked about governance health, accountability, ownership, leavers,
    or "what are our dashboards not telling us". Checks: owner concentration
    (bus factor), ownerless objects, owners with no manager, leavers whose accounts
    are still enabled (sensitive access flagged), privileged access granted
    directly outside the role model, and registered AI agents with orphaned owners.
    """
    try:
        roles, aps, sources, identities = await asyncio.gather(
            isc.list_all("/v3/roles"), isc.list_all("/v3/access-profiles"),
            isc.list_all("/v3/sources"), isc.search_all("identities", "*"),
        )
        agents, registry = await load_agents()
    except ISCError as exc:
        return {"error": str(exc)}

    by_id = {i["id"]: i for i in identities}
    objects = {"ROLE": roles, "ACCESS_PROFILE": aps, "SOURCE": sources}
    bf = bus_factor(objects)

    ownerless, owner_no_mgr = [], set()
    for t, objs in objects.items():
        for o in objs:
            ow = o.get("owner") or {}
            if not ow.get("id"):
                ownerless.append({"type": t, "id": o["id"], "name": o["name"], "reason": "NO_OWNER"})
                continue
            if ow.get("type") == "GOVERNANCE_GROUP":
                continue
            doc = by_id.get(ow["id"])
            if doc is None:
                ownerless.append({"type": t, "id": o["id"], "name": o["name"], "reason": "OWNER_NOT_FOUND"})
            elif is_inactive(doc):
                ownerless.append({"type": t, "id": o["id"], "name": o["name"], "reason": "OWNER_INACTIVE"})
            elif not doc.get("manager"):
                owner_no_mgr.add(doc["name"])

    leavers = []
    for i in identities:
        if not is_inactive(i):
            continue
        enabled = [(a.get("source") or {}).get("name") for a in i.get("accounts") or [] if a.get("disabled") is False]
        if enabled or i.get("accessCount"):
            access = [a["name"] for a in i.get("access") or []]
            leavers.append({"identity": i["name"], "id": i["id"], "department": (i.get("attributes") or {}).get("department"),
                            "enabledAccounts": enabled, "accessCount": i.get("accessCount"),
                            "sensitiveAccess": [n for n in access if SENSITIVE.search(n)], "modified": i.get("modified")})

    priv = [(i["name"], a) for i in identities for a in i.get("access") or [] if a.get("privileged")]
    priv_direct = [(n, a) for n, a in priv if a.get("standalone")]

    orphaned_agents = []
    for a in agents:
        chain = await _owner_chain(a.get("owner"))
        if chain["status"] != "OK":
            orphaned_agents.append({"agent": a["name"], "owner": a.get("owner"), "ownerStatus": chain["status"]})

    result = {
        "verdict": "Point checks pass, chain checks fail" if (not ownerless and (bf["topOwnerShare"] >= 0.5 or leavers)) else "See findings",
        "pointCheck": {"ownerlessObjects": len(ownerless)},
        "busFactor": {**bf, "topOwnerHasManager": bf["topOwner"] not in owner_no_mgr},
        "ownersWithoutManager": sorted(owner_no_mgr),
        "leaversWithLiveAccess": {"count": len(leavers), "enabledAccounts": sum(len(l["enabledAccounts"]) for l in leavers),
                                  "items": leavers[:max_items]},
        "privilegedGrants": {"total": len(priv), "direct": len(priv_direct),
                             "directShare": round(len(priv_direct) / len(priv), 2) if priv else 0.0,
                             "topDirect": Counter(a["name"] for _, a in priv_direct).most_common(5)},
        "agents": {"registry": registry, "registered": len(agents), "orphanedOwner": orphaned_agents},
        "scanned": {"roles": len(roles), "accessProfiles": len(aps), "sources": len(sources), "identities": len(identities)},
        "ownerless": ownerless[:max_items],
    }
    logger.info(f"event=accountability_scan identities={len(identities)} leavers={len(leavers)} bus_top_share={bf['topOwnerShare']}")
    return result


async def detect_rogue_agents(agent_name: Optional[str] = None) -> dict:
    """Detect rogue AI agents by walking each agent's accountability chain.

    Use when asked whether any AI agent is rogue, risky, orphaned, or over-privileged,
    or to assess a specific agent. Signals: ORPHANED_OWNER (owner inactive/missing),
    SOD_CONFLICT (agent's access violates a tenant SoD policy), PURPOSE_DRIFT (access
    beyond declared purpose), OWNER_NO_MANAGER, PRIVILEGED_DIRECT. Returns a 0-100
    risk score, severity, and evidence[] per agent. Read-only.
    """
    try:
        agents, registry = await load_agents()
        if agent_name:
            agents = [a for a in agents if a["name"].lower() == agent_name.lower()]
            if not agents:
                return {"error": f"Agent '{agent_name}' not in registry ({registry})."}
        pairs = await _sod_pairs()
        results = []
        for a in agents:
            ents = await _entitlements_by_name(a.get("entitlements") or [], a.get("sourceId"))
            held = {n: (ents.get(n) or {}).get("id") for n in a.get("entitlements") or []}
            chain = await _owner_chain(a.get("owner"))
            results.append(score_agent(a, chain, ents, sod_conflicts(held, pairs)))
    except ISCError as exc:
        return {"error": str(exc)}

    results.sort(key=lambda r: r["riskScore"], reverse=True)
    logger.info(f"event=rogue_scan agents={len(results)} rogue={sum(r['rogue'] for r in results)}")
    return {"registry": registry, "scannedAt": _now(), "rogueCount": sum(r["rogue"] for r in results), "agents": results}


async def quarantine_agent(agent_name: str, reason: str, confirm: bool = False) -> dict:
    """Quarantine an AI agent. DRY RUN by default; only confirm=True acts.

    Use after detect_rogue_agents flags an agent. Always call first with
    confirm=False and show the plan to the human; call with confirm=True only after
    the human explicitly approves. Actions on confirm: (1) deactivate the agent in
    the registry (ISC DEACTIVATE lifecycle action when registered in ISC), (2) disable
    the agent's account in its target application. Entitlement revocation and owner
    reassignment are recommended, not executed.
    """
    if not reason.strip():
        return {"error": "reason is required (it is written to the audit log)."}
    detection = await detect_rogue_agents(agent_name)
    if "error" in detection:
        return detection
    finding = detection["agents"][0]
    agents, registry = await load_agents()
    agent = next(a for a in agents if a["name"] == finding["agent"])
    chain = finding["ownerChain"]

    target = None
    if agent.get("targetAccount") and target_app.configured():
        try:
            target = await target_app.find_account(agent["targetAccount"])
        except target_app.TargetAppError as exc:
            target = {"error": str(exc)}

    plan = [
        {"step": 1, "action": "DEACTIVATE_AGENT",
         "how": {"machine": f"ISC machine-identity lifecycle action DEACTIVATE on {agent.get('id')}",
                 "source": f"ISC tag {QUARANTINE_TAG} on agent account {agent.get('accountId')} and identity "
                           f"{agent.get('identityId')} (source {agent.get('sourceName')}); account disable attempted best-effort",
                 "local": "Set registry status QUARANTINED (local registry)"}[_registry_kind(registry)],
         "executes": True},
        {"step": 2, "action": "DISABLE_TARGET_ACCOUNT",
         "how": (f"POST /v1/users/{target['id']}/disable on target app" if target and target.get("id")
                 else f"Skipped: {'target app key not configured' if not target_app.configured() else (target or {}).get('error', 'no target account found')}"),
         "executes": bool(target and target.get("id"))},
        {"step": 3, "action": "REVOKE_ACCESS (recommended)",
         "how": f"Remove {[s['detail'] for s in finding['signals'] if s['signal'] in ('PURPOSE_DRIFT', 'SOD_CONFLICT')]} via access request; phase 2",
         "executes": False},
        {"step": 4, "action": "REASSIGN_OWNER (recommended)",
         "how": f"Owner {chain.get('owner')} is {chain['status']}; escalate to {chain['escalateTo']} for a new accountable owner",
         "executes": False},
    ]
    base = {"agent": agent["name"], "riskScore": finding["riskScore"], "severity": finding["severity"],
            "signals": [s["signal"] for s in finding["signals"]], "reason": reason, "plan": plan}

    if not confirm:
        logger.info(f"event=quarantine_planned agent={agent['name']} score={finding['riskScore']}")
        return {**base, "mode": "DRY_RUN", "next": "Show this plan to the human. Re-run with confirm=true only after explicit approval."}

    results = []
    try:
        kind = _registry_kind(registry)
        if kind == "machine":
            resp = await isc.request("POST", f"/machine-identities/v1/{agent['id']}/lifecycle-actions", headers=EXPERIMENTAL,
                                     json={"action": "DEACTIVATE", "comments": [{"comment": reason[:1000]}]})
            body = resp.json()
            results.append({"step": 1, "result": "SUBMITTED", "requestId": body.get("requestId"), "status": body.get("status")})
        elif kind == "source":
            tagged = await set_quarantine_tag(agent, on=True)
            disable = "SKIPPED"
            try:  # flat-file sources usually can't provision; never let this block containment
                await isc.request("POST", f"/v3/accounts/{agent['accountId']}/disable", json={"forceProvisioning": False})
                disable = "SUBMITTED"
            except ISCError as exc:
                disable = f"NOT_SUPPORTED ({exc})"
            results.append({"step": 1, "result": "TAGGED", "tag": QUARANTINE_TAG, "taggedObjects": tagged, "accountDisable": disable})
        else:
            _save_local_status(agent["name"], "QUARANTINED", reason)
            results.append({"step": 1, "result": "QUARANTINED", "registry": registry})
    except ISCError as exc:
        results.append({"step": 1, "result": "FAILED", "error": str(exc)})

    if target and target.get("id"):
        try:
            acct = await target_app.disable_account(target["id"])
            results.append({"step": 2, "result": "DISABLED", "accountId": target["id"], "active": acct.get("active")})
        except target_app.TargetAppError as exc:
            results.append({"step": 2, "result": "FAILED", "error": str(exc)})

    logger.warning(f"event=quarantine_executed agent={agent['name']} score={finding['riskScore']} "
                   f"reason=\"{reason[:200]}\" results={results}")
    return {**base, "mode": "EXECUTED", "executedAt": _now(), "results": results}
