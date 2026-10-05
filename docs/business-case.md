# Green Isn't Safe
### Catching a rogue AI agent through its accountability chain, then containing it with a human in the loop

**Team:** Sai Ravula · Alex · Muyiwa (Cox Automotive, IAM & Data Protection)
**Built on:** SailPoint ISC APIs + MCP (Python FastMCP) · demo tenant `devrel-ga-25087`
**Date:** 2026-10-05, SailPoint Navigate Hack Day

> **Narrative anchor:** *Your dashboards say green. Ask the agent what they're not telling you.*

---

## 1. The problem

AI agents are arriving in identity programs faster than governance is adapting. Each agent gets access, an owner and a purpose, and then **the chain behind it decays quietly**:

- The **owner leaves** the company, but the agent keeps running.
- The agent **gains access beyond its declared purpose**, one direct grant at a time.
- Its access combination **violates separation of duties** (it can both initiate and receive payments).

Every point check still passes: the agent is registered, it has an owner, and its account is active. **Nobody is accountable, and it can move money.**

**Root cause:** accountability is a property of the chain (agent → access → owner → owner's lifecycle → owner's manager), but ISC is viewed one object at a time. No single screen shows the chain, so no one checks it. Humans already have this gap; agents inherit it.

---

## 2. Evidence: measured live in the demo tenant today

**The human gaps agents inherit (the tenant's own data):**

| Finding | Measured |
|---|---|
| Ownership check passes, bus factor is 1 | Ownerless check = **0**. Yet **45 of 47** roles, access profiles and sources (**96%**) are owned by **one identity, who has no manager**. |
| Leavers keep live accounts | **9 of 9** inactive identities: **27 accounts, all enabled**. Denise.Hunt's AD `userAccountControl = 66048` (enabled, password never expires). |
| Leavers hold sensitive access | `ENG_Prod`, `HostingVPN`, `Treasury` are still live for departed users |
| Privileged access outside the role model | **33 of 51** privileged grants (**65%**) are direct grants |

**The staged agent fleet (we say this openly):** 5 AI agents aggregated from a `Bots` source in ISC. The agents are staged. **Their owners, the leaver status, the entitlements and the SoD policy are real ISC objects.**

| Agent | Owner (real identity) | Detected | Score |
|---|---|---|---|
| **invoice-bot** | Denise.Hunt, *inactive leaver* | Orphaned owner · access beyond declared purpose · **violates ENFORCED SoD policy "Agent – Money In and Out"** | **90 CRITICAL** |
| deploy-bot | Sandra.Lopez, *inactive leaver* | Orphaned owner · holds `ENG_Prod`, declared staging only | 60 HIGH |
| payroll-sync-bot | samantha.holstine | Owner has no manager (the bus-factor identity) | 10 LOW |
| green-isnt-safe-governor *(our agent)* | hack.day | Owner has no manager | 10 LOW |
| hr-onboarding-bot | Evelyn.Ellis, *active, has manager* | Nothing. The clean comparison case. | 0 LOW |

invoice-bot scores 90 and hr-onboarding-bot scores 0, so one agent gets flagged, not five.

**What we checked and dropped:** an early run matched invoice-bot to the tenant's AD SoD policy **by entitlement name**. That's a false positive, because the policy covers different entitlements. We changed matching to **entitlement IDs** and created a real policy for the agent source.

---

## 3. The solution: Explain → Detect → Contain

| Capability | The question | Tool | Mode |
|---|---|---|---|
| **Explain** | "Why does invoice-bot have AccountsReceivable?" | `explain_access`: role → access profile → entitlement path, or **direct grant**, checked against the declared purpose. Works for humans too. | Read-only |
| **Expose** | "Is our governance actually healthy?" | `find_accountability_gaps`: bus factor, leavers with live accounts, direct privileged grants, orphaned agents | Read-only |
| **Detect** | "Is any AI agent rogue?" | `detect_rogue_agents`: walks each agent's chain, scores it 0–100, returns signals with `evidence[]` | Read-only |
| **Contain** | "Quarantine it." | `quarantine_agent`: **dry run by default.** On human confirmation: tags the agent `AGENT_QUARANTINED` in ISC (account and identity) **and disables its account in the target application** | Human-confirmed |

**Every answer includes `evidence[]`** (object IDs and timestamps), so an auditor can replay each claim against ISC.

### Why not a saved report?
- **Reports answer the questions you already knew to ask.** invoice-bot passes every point check. Only following the chain (agent → owner → owner is inactive → owner's manager) surfaces it.
- **Detect to contain in one conversation.** "Is any agent rogue?" → "Why does it have that?" → "Quarantine it." → "Confirmed." As tickets, that's three teams and a week.
- **The same tools cover humans and agents.** The chain logic that catches invoice-bot also catches the 9 leavers.

---

## 4. Value

### Risk: the headline
| Metric | Today | Target |
|---|---|---|
| **Agents with an orphaned owner** | **2 of 5** | 0. Every agent has an active, accountable owner. |
| **Agents violating SoD** | **1 of 5** | 0 |
| **Time from detection to containment** | Manual discovery, owner lookup, then a ticket to the app team (not yet baselined) | **One conversation**; each tool call takes under 5 seconds |
| **Governance bus factor** | **96%** (45 / 47) | No owner above 20% |
| **Leaver residue** | **9 / 9** with enabled accounts | 0 within 24 h |

These map to controls auditors already test (SOX ITGC access reviews, timely deprovisioning, SoD) and now extend them to non-human identities.

### Efficiency
```
hours saved / month = investigations × (minutes now − minutes with agent) ÷ 60
```
*Illustrative only:* 100 investigations a month × 40 minutes saved ≈ **67 analyst-hours a month (~0.4 FTE)**. The 40 minutes comes from the team's 30–60 minute estimate per "why does X have Y" case and is replaced by the pilot baseline.

---

## 5. Guardrails
- **4 of 5 tools are read-only.** Containment is **dry run first, enforced by the server**: `confirm=true` is refused without the token from a dry run of the same agent at the same risk score in the last 10 minutes.
- **Containment can be reversed.** A tag plus a disable is undone with `reset_demo.py`. Revoking access and reassigning the owner are *recommended*, not executed (phase 2, through ISC Workflows).
- **Credentials live in the OS vault** (macOS Keychain or Windows Credential Manager). No secrets on disk.
- **Every ISC call is logged** in Splunk-ready key=value format, and containment is logged at WARN with the human's stated reason. Control characters are stripped, so a crafted reason can't forge log lines.
- **Untrusted input is escaped** before it reaches ISC search or filter strings. Identity names come from the model and entitlement names from agent data.
- **Least privilege in production:** the demo uses the lab-required `sp:scopes:all` PAT. Production uses a scoped client: read for detection, plus one narrowly scoped write for tagging.
- **Rehearsed and verified:** containment ran live twice today. The flat-file account disable isn't supported, which **we found in rehearsal**, so containment uses the ISC tag plus the target-app disable.

---

## 6. Pilot and roadmap
| Phase | Adds |
|---|---|
| **1 (today)** | Explain, Expose, Detect, Contain (tag and target-app disable), all human-confirmed |
| 2 | Native ISC machine-identity `DEACTIVATE` once agents are aggregated from AI-platform sources. Revoke and reassign through Workflows. |
| 3 | Scheduled scans that alert on new orphaned or SoD-violating agents. Join with ISC Agent Behavior Monitoring anomalies. |
| 4 | Agent ownership succession: when an owner leaves, automatically route the agent to the owner's manager for re-attestation |

**30-day pilot:** run detection weekly across all registered agents. Measure orphaned agents, SoD-violating agents and detection-to-containment time. Exit criterion: **every CRITICAL finding contained within 1 business day.**

---

## 7. Demo script (3 minutes)
**Before going on stage:** `python reset_demo.py --apply` → both systems show ACTIVE with no tags.

| Time | Who | Ask the agent | The moment |
|---|---|---|---|
| 0:00 | Muyiwa | *(frame)* "AI agents are getting access faster than governance can keep up…" | The problem |
| 0:20 | Sai | "Is our governance healthy?" | Ownerless = 0 ✅ … but **45 of 47 objects owned by one person with no manager**, and **9 of 9 leavers still enabled**. "Agents inherit this." |
| 0:55 | Sai | "Are any of our AI agents rogue?" | **invoice-bot 90 CRITICAL**: owner left, access beyond purpose, real SoD violation. hr-onboarding-bot **0**. |
| 1:30 | Alex | "Why does invoice-bot have AccountsReceivable?" | **Direct grant, no role justifies it, outside its declared purpose** |
| 1:55 | Sai | "Quarantine invoice-bot." | **Dry-run plan** appears. "Nothing happens until a human approves." |
| 2:15 | Sai | "Confirmed. Proceed." | Tagged in ISC, **disabled in the target app**. Re-run detection: **QUARANTINED**. Escalated to **Catherine.Simmons**, Denise's manager. |
| 2:40 | Muyiwa | *(close)* Value, guardrails, pilot | "Your dashboards say green…" |

## 8. Anticipated judge questions
| Question | Answer |
|---|---|
| "Are the agents real?" | **They're staged, and we say so.** Their owners, the leaver status, the entitlements and the SoD policy are real ISC objects. The human gaps in section 2 are the tenant's own data. |
| "Why not use ISC's native agent deactivation?" | It applies to machine identities aggregated from AI-platform sources. This tenant has no AI-agent source configured, so we tag in ISC and disable at the target app. Native `DEACTIVATE` is phase 2, and the code path already exists. |
| "Couldn't a report do this?" | A report shows one link of the chain. The agent walks the whole chain and then acts on it, with a human approving. |
| "What if the AI quarantines the wrong agent?" | It can't act alone. The server refuses `confirm=true` without a fresh token from its own dry run, the MCP client asks the human before a destructive tool runs, and every action can be reversed. |
| "A tag isn't containment." | Correct. The target-app disable is what stops the bot. The ISC tag is the governance record that says it was quarantined, by whom, and why. |
| "Who decided an owner leaving is worth 40?" | The weights are deliberately simple and explainable: no accountable human (40) outranks a toxic access combination (30), which outranks drift (20). They live in one dict and are unit-tested. |
| "Can a rogue agent prompt-inject you through its own description?" | Its metadata does reach the model. Injected text can plan a quarantine, but it can't execute one: that needs the dry-run token and a human approving in the client. |
| "Isn't `sp:scopes:all` a risk?" | Yes, and the lab requires it. Production runs on a scoped client (section 5). |
| "Is the data cherry-picked?" | Every number was measured live today. We dropped one false-positive SoD match and one unsupported claim about campaigns. |

## 9. Team
| Person | Owns |
|---|---|
| **Alex** | `explain.py` (Explain), demo segment at 1:30 |
| **Sai** | `governance.py` (Expose, Detect, Contain), demo segments at 0:20, 0:55, 1:55 and 2:15 |
| **Muyiwa** | Business-case slide, framing and close, timekeeping, Q&A routing |
