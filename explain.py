"""
Explain tools (Alex's lane): why does this identity or agent have this access?

Traces the access path: role -> access profile -> entitlement -> source -> account,
or flags a DIRECT grant that no role or access profile justifies.
"""

import asyncio
from typing import Optional

import governance
from isc_client import ISCError, isc, lifecycle_state


def _ev(kind: str, obj_id: Optional[str], name: Optional[str], detail: str) -> dict:
    return {"type": kind, "id": obj_id, "name": name, "detail": detail}


async def _explain_agent(agent: dict, access_name: str, registry: str) -> dict:
    held = agent.get("entitlements") or []
    match = next((e for e in held if e.lower() == access_name.lower()), None)
    if not match:
        return {"subject": agent["name"], "subjectType": "AI_AGENT", "access": access_name, "holds": False,
                "summary": f"{agent['name']} does not hold {access_name}. It holds {held}."}
    declared = agent.get("declaredAccess") or []
    ents = await governance._entitlements_by_name([match], agent.get("sourceId"))
    e = ents.get(match) or {}
    within = match in declared
    return {
        "subject": agent["name"], "subjectType": "AI_AGENT", "access": match, "holds": True,
        "grantType": "DIRECT",
        "path": [f"source:{agent.get('sourceName', registry)}", f"account:{agent['name']}", f"entitlement:{match}"],
        "justifiedByRoleOrAccessProfile": False,
        "withinDeclaredPurpose": within,
        "owner": agent.get("owner"),
        "summary": (f"{agent['name']} holds {match} as a DIRECT grant on its account. No role or access profile "
                    f"justifies it, and it is {'within' if within else 'OUTSIDE'} the agent's declared purpose {declared}."),
        "evidence": [_ev("ENTITLEMENT", e.get("id"), match, f"source={agent.get('sourceName')}"),
                     _ev("ACCOUNT", agent.get("accountId"), agent["name"], f"aggregated={agent.get('aggregated')}")],
    }


async def explain_access(identity: str, access_name: str) -> dict:
    """Explain why an identity or AI agent has a specific access item.

    Use for "why does X have Y?", "how did X get Y?", or audit questions about an
    access path. Works for people and for registered AI agents. Returns the grant
    type (ROLE, ACCESS_PROFILE, or DIRECT), the path from role to entitlement to
    account, whether a role/access profile justifies it, and evidence[] with ids.
    """
    if not identity.strip() or not access_name.strip():
        return {"error": "identity and access_name are required"}
    try:
        agents, registry = await governance.load_agents()
        agent = next((a for a in agents if a["name"].lower() == identity.strip().lower()), None)
        if agent:
            return await _explain_agent(agent, access_name.strip(), registry)

        doc = await isc.identity_by_name(identity.strip())
        if not doc:
            return {"error": f"Identity '{identity}' not found."}
        access = doc.get("access") or []
        item = next((a for a in access if a.get("name", "").lower() == access_name.strip().lower()), None)
        if not item:
            return {"subject": doc["name"], "access": access_name, "holds": False,
                    "summary": f"{doc['name']} does not hold {access_name}.",
                    "holdsInstead": sorted(a["name"] for a in access)[:25]}

        src = (item.get("source") or {}).get("name")
        account = next((a for a in doc.get("accounts") or [] if (a.get("source") or {}).get("name") == src), None)
        evidence = [_ev(item.get("type"), item.get("id"), item.get("name"), f"source={src} privileged={item.get('privileged')}")]
        if account:
            evidence.append(_ev("ACCOUNT", account.get("id"), account.get("name"), f"source={src} disabled={account.get('disabled')}"))

        grant_type, path, via = "DIRECT", [f"identity:{doc['name']}"], []
        if item.get("type") == "ENTITLEMENT" and not item.get("standalone"):
            held_aps = [a for a in access if a.get("type") == "ACCESS_PROFILE"]
            details = await asyncio.gather(*(isc.request("GET", f"/v3/access-profiles/{a['id']}") for a in held_aps))
            for ap in (d.json() for d in details):
                if any(e.get("id") == item["id"] for e in ap.get("entitlements") or []):
                    via.append(ap)
            if via:
                grant_type = "ACCESS_PROFILE"
                path += [f"accessProfile:{via[0]['name']}"]
                evidence += [_ev("ACCESS_PROFILE", ap["id"], ap["name"], "contains entitlement") for ap in via]
                roles = [a for a in access if a.get("type") == "ROLE"]
                role_docs = await asyncio.gather(*(isc.request("GET", f"/v3/roles/{r['id']}") for r in roles))
                for r in (d.json() for d in role_docs):
                    if any(p.get("id") in {v["id"] for v in via} for p in r.get("accessProfiles") or []):
                        grant_type = "ROLE"
                        path.insert(1, f"role:{r['name']}")
                        evidence.append(_ev("ROLE", r["id"], r["name"], "includes access profile"))
                        break
        path += [f"{item.get('type', '').lower()}:{item['name']}", f"account:{src}"]

        justified = grant_type != "DIRECT"
        return {
            "subject": doc["name"], "subjectType": "IDENTITY", "lifecycleState": lifecycle_state(doc),
            "access": item["name"], "holds": True, "grantType": grant_type, "path": path,
            "justifiedByRoleOrAccessProfile": justified, "privileged": item.get("privileged"),
            "summary": (f"{doc['name']} holds {item['name']} ({src}) via {' -> '.join(path[1:-1]) or 'a direct grant'}."
                        if justified else
                        f"{doc['name']} holds {item['name']} ({src}) as a DIRECT grant. No role or access profile justifies it."),
            "evidence": evidence,
        }
    except ISCError as exc:
        return {"error": str(exc)}
