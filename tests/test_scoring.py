"""
Offline unit tests for the detection logic. No network, no credentials.

Run:  python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import governance as g  # noqa: E402

PAIRS = [{
    "name": "Agent - Money In and Out", "id": "sod-1", "state": "ENFORCED",
    "left": {"AccountsPayable"}, "right": {"AccountsReceivable"},
    "leftIds": {"ent-ap-bots"}, "rightIds": {"ent-ar-bots"},
}]


def chain(status="OK", manager="Catherine.Simmons", owner="Denise.Hunt"):
    return {"owner": owner, "ownerId": "id-owner", "status": status, "lifecycleState": "inactive" if status != "OK" else "active",
            "manager": manager, "escalateTo": manager or g.FALLBACK_GOVERNANCE_OWNER, "ownerEnabledAccounts": []}


class SodMatching(unittest.TestCase):
    def test_matches_on_entitlement_id(self):
        held = {"AccountsPayable": "ent-ap-bots", "AccountsReceivable": "ent-ar-bots"}
        out = g.sod_conflicts(held, PAIRS)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["matchedOn"], "id")

    def test_same_name_different_source_does_not_match(self):
        """The false positive we caught live: AD policy vs same-named Bots entitlements."""
        held = {"AccountsPayable": "ent-ap-AD", "AccountsReceivable": "ent-ar-AD"}
        self.assertEqual(g.sod_conflicts(held, PAIRS), [])

    def test_name_fallback_only_when_ids_unresolved(self):
        held = {"AccountsPayable": None, "AccountsReceivable": None}
        out = g.sod_conflicts(held, PAIRS)
        self.assertEqual(out[0]["matchedOn"], "name")

    def test_one_side_only_is_not_a_conflict(self):
        self.assertEqual(g.sod_conflicts({"AccountsPayable": "ent-ap-bots"}, PAIRS), [])


class AgentScoring(unittest.TestCase):
    def test_invoice_bot_is_critical(self):
        agent = {"name": "invoice-bot", "entitlements": ["AccountsPayable", "AccountsReceivable"],
                 "declaredAccess": ["AccountsPayable"], "status": "ACTIVE"}
        conflicts = g.sod_conflicts({"AccountsPayable": "ent-ap-bots", "AccountsReceivable": "ent-ar-bots"}, PAIRS)
        r = g.score_agent(agent, chain("OWNER_INACTIVE"), {}, conflicts)
        self.assertEqual(r["riskScore"], 90)   # 40 orphaned + 30 SoD + 20 drift
        self.assertEqual(r["severity"], "CRITICAL")
        self.assertTrue(r["rogue"])
        self.assertEqual({s["signal"] for s in r["signals"]}, {"ORPHANED_OWNER", "SOD_CONFLICT", "PURPOSE_DRIFT"})

    def test_clean_agent_scores_zero(self):
        agent = {"name": "hr-onboarding-bot", "entitlements": ["HRRead"], "declaredAccess": ["HRRead"]}
        r = g.score_agent(agent, chain("OK", owner="Evelyn.Ellis", manager="Peter.Powell"), {}, [])
        self.assertEqual((r["riskScore"], r["severity"], r["rogue"]), (0, "LOW", False))

    def test_owner_without_manager_is_low_not_rogue(self):
        agent = {"name": "payroll-sync-bot", "entitlements": ["PayrollRead"], "declaredAccess": ["PayrollRead"]}
        r = g.score_agent(agent, chain("OK", owner="samantha.holstine", manager=None), {}, [])
        self.assertEqual(r["riskScore"], 10)
        self.assertFalse(r["rogue"])

    def test_privileged_direct_grant_adds_weight(self):
        agent = {"name": "x", "entitlements": ["Admins"], "declaredAccess": ["Admins"]}
        r = g.score_agent(agent, chain("OK"), {"Admins": {"id": "e1", "privileged": True}}, [])
        self.assertIn("PRIVILEGED_DIRECT", {s["signal"] for s in r["signals"]})

    def test_score_is_capped_at_100(self):
        agent = {"name": "x", "entitlements": ["AccountsPayable", "AccountsReceivable"], "declaredAccess": []}
        ents = {"AccountsPayable": {"privileged": True}, "AccountsReceivable": {"privileged": True}}
        conflicts = g.sod_conflicts({"AccountsPayable": "ent-ap-bots", "AccountsReceivable": "ent-ar-bots"}, PAIRS)
        r = g.score_agent(agent, chain("OWNER_INACTIVE", manager=None), ents, conflicts)
        self.assertLessEqual(r["riskScore"], 100)


class Helpers(unittest.TestCase):
    def test_bus_factor(self):
        objs = {"ROLE": [{"owner": {"name": "sam"}}] * 3, "SOURCE": [{"owner": {"name": "ops"}}, {"owner": None}]}
        bf = g.bus_factor(objs)
        self.assertEqual((bf["topOwner"], bf["topOwnerObjects"], bf["objects"]), ("sam", 3, 5))
        self.assertEqual(bf["topOwnerShare"], 0.6)

    def test_severity_bands(self):
        self.assertEqual([g.severity(s) for s in (0, 20, 40, 70, 100)], ["LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL"])

    def test_registry_kind_routing(self):
        """Regression: the Bots source registry must not route to machine-identity DEACTIVATE."""
        self.assertEqual(g._registry_kind("isc:/machine-identities/v2"), "machine")
        self.assertEqual(g._registry_kind("isc:source:Bots"), "source")
        self.assertEqual(g._registry_kind("local:agents.json"), "local")

    def test_as_list(self):
        self.assertEqual(g._as_list(None), [])
        self.assertEqual(g._as_list(""), [])
        self.assertEqual(g._as_list("A;B"), ["A", "B"])
        self.assertEqual(g._as_list(["A"]), ["A"])


if __name__ == "__main__":
    unittest.main()
