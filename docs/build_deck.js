// "Green Isn't Safe": Navigate 2026 Hack Day deck (pptxgenjs, structured deck)
// Build: npm install pptxgenjs && APPLY_THEME_JS=/path/to/apply_theme.js node build_deck.js
const pptxgen = require("pptxgenjs");
// Theme colors are written by apply_theme.js from the pptx skill. Point APPLY_THEME_JS at it;
// without it the deck still builds, using Office's stock palette for scheme colors.
const path = require("path");
let applyTheme = null;
try { ({ applyTheme } = require(process.env.APPLY_THEME_JS || "./apply_theme.js")); } catch { console.warn("apply_theme.js not found; skipping theme colors"); }

const OUT = path.join(__dirname, "Green-Isnt-Safe-Navigate26.pptx");

const THEME = {
  name: "Green Isnt Safe",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0E1726", lt1: "FFFFFF", dk2: "425166", lt2: "F2F4F7",
    accent1: "17B26A", accent2: "E5484D", accent3: "F5A524", accent4: "64748B", accent5: "2E7CF6", accent6: "1E2B3D",
    hlink: "2E7CF6", folHlink: "64748B",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Green Isn't Safe";
pres.subject = "SailPoint Navigate 2026 Hack Day - MCP Server track";
pres.author = "Sai Ravula, Alex, Muyiwa";
const C = pres.SchemeColor;

const W = 13.333, M = 0.6;

// ---------- Layouts ----------
pres.defineSlideMaster({
  title: "DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 1.7, w: W - 2 * M, h: 1.5, fontFace: "Cambria", fontSize: 54, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 3.35, w: 9.5, h: 1.2, fontSize: 20, color: "C7D0DC", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.4, w: W - 2 * M, h: 0.9, fontFace: "Cambria", fontSize: 34, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "Green Isn't Safe  ·  SailPoint Navigate 2026 Hack Day", options: { x: M, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});

// ---------- Helpers ----------
let n = 0;
const id = (p) => `${p}-${++n}`;
function pill(slide, x, y, w, kind, label, opts = {}) {
  const ok = kind === "PASS";
  const h = opts.h || 0.5;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: h / 2, objectName: id("pill"),
    fill: { color: ok ? "E7F7EF" : "FDECEC" }, line: { color: ok ? C.accent1 : C.accent2, width: 1.25 },
  });
  slide.addText([
    { text: kind, options: { bold: true, color: ok ? C.accent1 : C.accent2, fontSize: opts.tagSize || 13 } },
    { text: "   " + label, options: { color: C.text1, fontSize: opts.size || 14 } },
  ], { x: x + 0.2, y, w: w - 0.3, h, valign: "middle", margin: 0, isTextBox: true, objectName: id("pilltxt"), fit: "shrink" });
}
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: id("card") });
}
function circleNum(slide, x, y, num, color) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.55, h: 0.55, fill: { color }, line: { color, width: 0 }, objectName: id("num") });
  slide.addText(String(num), { x, y, w: 0.55, h: 0.55, align: "center", valign: "middle", bold: true, fontSize: 16, color: C.background1, margin: 0, isTextBox: true, objectName: id("numtxt") });
}

// ---------- 1. Title ----------
pres.addSection({ title: "Open" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Open" });
s.addText("Green Isn't Safe", { placeholder: "title" });
s.addText("Catching rogue AI agents through their accountability chain, then containing them with a human in the loop", { placeholder: "body" });
// Use PASS/FAIL text on the pills, not check/cross glyphs: the glyphs aren't guaranteed in Cambria or Calibri on every machine
const darkPill = (x, y, w, kind, label) => {
  const ok = kind === "PASS";
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.48, rectRadius: 0.24, fill: { color: "16233A" }, line: { color: ok ? C.accent1 : C.accent2, width: 1.25 }, objectName: id("pill") });
  s.addText([{ text: kind, options: { bold: true, color: ok ? C.accent1 : C.accent2 } }, { text: "   " + label, options: { color: "E6EBF2" } }],
    { x: x + 0.2, y, w: w - 0.3, h: 0.48, fontSize: 13, valign: "middle", margin: 0, isTextBox: true, objectName: id("pilltxt") });
};
darkPill(M, 4.75, 2.6, "PASS", "Agent registered");
darkPill(M + 2.8, 4.75, 2.4, "PASS", "Has an owner");
darkPill(M + 5.4, 4.75, 2.6, "PASS", "Account active");
darkPill(M + 8.2, 4.75, 3.9, "FAIL", "Owner left. Nobody is accountable.");
s.addText("Sai Ravula  ·  Alex  ·  Muyiwa", { x: M, y: 6.3, w: 7, h: 0.4, fontSize: 16, bold: true, color: C.background1, margin: 0, isTextBox: true, objectName: "team" });
s.addText("SailPoint Navigate 2026 Hack Day  ·  MCP Server track", { x: M, y: 6.7, w: 7, h: 0.35, fontSize: 13, color: "93A1B5", margin: 0, isTextBox: true, objectName: "event" });
s.addNotes("MUYIWA (0:00-0:20): AI agents are getting access faster than governance can keep up. Three of these checks pass. The fourth asks whether anyone is still accountable for the agent, and it fails. Today we'll show you how an MCP server catches that and contains it, with a human in the loop.");

// ---------- 2. Problem ----------
pres.addSection({ title: "Problem" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
s.addText("Every check passes. Nobody is accountable.", { placeholder: "title" });
s.addText("What the dashboard shows", { x: M, y: 1.55, w: 5.6, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "dash-h" });
pill(s, M, 2.15, 5.6, "PASS", "invoice-bot is registered and has an owner");
pill(s, M, 2.8, 5.6, "PASS", "Its account is active on the source");
pill(s, M, 3.45, 5.6, "PASS", "Ownership check: 0 ownerless objects");
s.addText("What the chain shows", { x: 6.9, y: 1.55, w: 5.8, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "chain-h" });
pill(s, 6.9, 2.15, 5.83, "FAIL", "Owner Denise.Hunt left the company");
pill(s, 6.9, 2.8, 5.83, "FAIL", "Holds AccountsReceivable beyond its declared purpose");
pill(s, 6.9, 3.45, 5.83, "FAIL", "Violates ENFORCED SoD policy: Money In and Out");
// chain row
const chain = ["AI agent", "Entitlements", "Declared purpose + SoD", "Owner", "Owner lifecycle", "Owner's manager"];
const cw = 1.8, gap = 0.26, cy = 4.85;
s.addText("Accountability is a chain. ISC is viewed one object at a time.", { x: M, y: 4.3, w: 12, h: 0.4, fontSize: 15, italic: true, color: C.text2, margin: 0, isTextBox: true, objectName: "chain-cap" });
chain.forEach((t, i) => {
  const x = M + i * (cw + gap);
  card(s, x, cy, cw, 0.85, i === 0 ? C.text1 : C.background2);
  s.addText(t, { x, y: cy, w: cw, h: 0.85, align: "center", valign: "middle", fontSize: 12, bold: i === 0, color: i === 0 ? C.background1 : C.text1, margin: 0.05, isTextBox: true, objectName: id("chain") });
  if (i < chain.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + cw + 0.04, y: cy + 0.32, w: 0.18, h: 0.22, fill: { color: C.accent4 }, line: { color: C.accent4, width: 0 }, objectName: id("arrow") });
});
s.addText("No single ISC screen shows this chain, so no one checks it.", { x: M, y: 6.0, w: 12, h: 0.5, fontSize: 15, color: C.text1, margin: 0, isTextBox: true, objectName: "root" });
s.addNotes("SAI: Point checks look at one object. Accountability lives in the chain: agent, access, purpose, owner, the owner's lifecycle, the owner's manager. invoice-bot passes every point check on the left and fails every chain check on the right.");

// ---------- 3. Evidence ----------
pres.addSection({ title: "Evidence" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("Agents inherit the gaps humans already have", { placeholder: "title" });
const stats = [
  { big: "0", unit: "", label: "ownerless objects", sub: "The standard check passes", color: C.accent1 },
  { big: "96%", unit: "", label: "of governed objects owned by one person", sub: "45 of 47, and she has no manager", color: C.accent2 },
  { big: "9 / 9", unit: "", label: "leavers still have enabled accounts", sub: "27 accounts, incl. AD with password never expires", color: C.accent2 },
  { big: "65%", unit: "", label: "of privileged grants are direct", sub: "33 of 51, with no role or access profile", color: C.accent3 },
];
const sw = 2.85, sg = 0.25;
stats.forEach((st, i) => {
  const x = M + i * (sw + sg);
  card(s, x, 1.65, sw, 3.55);
  s.addText(st.big, { x: x + 0.25, y: 1.95, w: sw - 0.5, h: 1.3, fontFace: "Cambria", fontSize: 60, bold: true, color: st.color, margin: 0, isTextBox: true, objectName: id("stat") });
  s.addText(st.label, { x: x + 0.25, y: 3.3, w: sw - 0.5, h: 0.9, fontSize: 17, bold: true, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: id("statlbl") });
  s.addText(st.sub, { x: x + 0.25, y: 4.25, w: sw - 0.5, h: 0.85, fontSize: 14, color: C.text2, valign: "top", margin: 0, isTextBox: true, objectName: id("statsub") });
});
s.addText("Measured live in the demo tenant today. We dropped two claims the data didn't support.", { x: M, y: 5.5, w: 12, h: 0.4, fontSize: 13, italic: true, color: C.accent4, margin: 0, isTextBox: true, objectName: "measured" });
s.addNotes("SAI (0:20-0:55): Is our governance healthy? The point check says yes: zero ownerless objects. The chain says no: one person with no manager owns 96% of governed objects, every leaver still has enabled accounts, and two-thirds of privileged access was granted directly. Agents inherit exactly this.");

// ---------- 4. Solution ----------
pres.addSection({ title: "Solution" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
s.addText("An MCP server that walks the chain", { placeholder: "title" });
const caps = [
  { n: 1, h: "Explain", q: "Why does invoice-bot have AccountsReceivable?", t: "explain_access", c: C.accent5 },
  { n: 2, h: "Expose", q: "Is our governance actually healthy?", t: "find_accountability_gaps", c: C.accent3 },
  { n: 3, h: "Detect", q: "Are any of our AI agents rogue?", t: "detect_rogue_agents", c: C.accent2 },
  { n: 4, h: "Contain", q: "Quarantine invoice-bot. (Human confirms.)", t: "quarantine_agent", c: C.accent1 },
];
const kw = 2.85, kg = 0.25;
caps.forEach((k, i) => {
  const x = M + i * (kw + kg);
  card(s, x, 1.65, kw, 3.2);
  circleNum(s, x + 0.25, 1.9, k.n, k.c);
  s.addText(k.h, { x: x + 0.95, y: 1.9, w: kw - 1.1, h: 0.55, fontFace: "Cambria", fontSize: 24, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true, objectName: id("caph") });
  s.addText(`"${k.q}"`, { x: x + 0.25, y: 2.7, w: kw - 0.5, h: 1.3, fontSize: 16, italic: true, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: id("capq") });
  s.addText(k.t, { x: x + 0.2, y: 4.15, w: kw - 0.35, h: 0.45, fontFace: "Courier New", fontSize: 11, color: C.text2, valign: "middle", margin: 0, isTextBox: true, objectName: id("capt") });
});
s.addText([
  { text: "Every answer carries evidence[]", options: { bold: true, color: C.text1 } },
  { text: " (ISC object IDs and timestamps), so an auditor can replay every claim.", options: { color: C.text2 } },
], { x: M, y: 5.2, w: 12.1, h: 0.6, fontSize: 15, margin: 0, isTextBox: true, objectName: "evidence" });
s.addNotes("BACKUP SLIDE (skip if the live demo works). SAI: Four tools: explain, expose, detect, contain. Four of the five are read-only. Python FastMCP on the ISC APIs, credentials only in the OS vault, every call logged.");


// ---------- 4b. How the MCP server works ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
s.addText("How the MCP server works", { placeholder: "title" });
const arch = [
  { t: "You ask in plain English", d: "\"Are any agents rogue?\"", dark: false },
  { t: "Claude picks a tool", d: "Any MCP client: Claude Code, Desktop, Cursor", dark: false },
  { t: "MCP server", d: "Python FastMCP, runs locally over stdio", dark: true },
  { t: "SailPoint ISC APIs", d: "Plus the agent's target app for containment", dark: false },
];
const aw = 2.75, ag = 0.37;
arch.forEach((a, i) => {
  const x = M + i * (aw + ag);
  card(s, x, 1.5, aw, 1.15, a.dark ? C.text1 : C.background2);
  s.addText([{ text: a.t, options: { bold: true, fontSize: 15, color: a.dark ? C.background1 : C.text1, breakLine: true } },
             { text: a.d, options: { fontSize: 12, color: a.dark ? "C7D0DC" : C.text2 } }],
    { x: x + 0.18, y: 1.5, w: aw - 0.3, h: 1.15, valign: "middle", margin: 0, isTextBox: true, objectName: id("arch") });
  if (i < arch.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + aw + 0.07, y: 1.95, w: 0.22, h: 0.26, fill: { color: C.accent4 }, line: { color: C.accent4, width: 0 }, objectName: id("aarrow") });
});
const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk1 }, fontSize: 13 } });
const mono = (t) => ({ text: t, options: { fontFace: "Courier New", fontSize: 12, bold: true, color: HEX.dk1 } });
const cell = (t, o = {}) => ({ text: t, options: { fontSize: 13, color: HEX.dk1, ...o } });
const ro = cell("Read-only", { color: HEX.accent1, bold: true });
const rows = [
  [hdr("Tool"), hdr("Answers"), hdr("ISC APIs it calls"), hdr("Mode")],
  [mono("search_identities"), cell("Who is this person?"), cell("/v3/search"), ro],
  [mono("explain_access"), cell("Why does X have Y?"), cell("search, access-profiles, roles"), ro],
  [mono("find_accountability_gaps"), cell("Is governance healthy?"), cell("roles, access-profiles, sources, search"), ro],
  [mono("detect_rogue_agents"), cell("Is any agent rogue?"), cell("accounts, entitlements, sod-policies, search"), ro],
  [mono("quarantine_agent"), cell("Contain this agent"), cell("tagged-objects, plus the target app"), cell("Dry run, then token + human", { color: HEX.accent2, bold: true })],
];
s.addTable(rows, {
  x: M, y: 2.95, w: W - 2 * M, colW: [3.0, 2.55, 4.0, 2.58], rowH: 0.48, valign: "middle",
  border: { type: "solid", pt: 0.75, color: "D5DBE3" }, fill: { color: HEX.lt1 }, margin: [0, 0.1, 0, 0.12], objectName: "tools-table",
});
s.addText("Credentials come from macOS Keychain or Windows Credential Manager. Every ISC call is logged with a correlation ID.",
  { x: M, y: 6.25, w: 12.1, h: 0.4, fontSize: 13, italic: true, color: C.accent4, margin: 0, isTextBox: true, objectName: "mcp-foot" });
s.addNotes("SAI or ALEX (about 20 seconds): MCP lets any AI client call our tools. You ask in plain English, Claude picks the tool, our server calls the ISC APIs and returns the answer with evidence. Four tools only read. The fifth, quarantine, runs a dry run first, and the server refuses to act without the token from that dry run and a human approving.");

// ---------- 5. Detection result ----------
pres.addSection({ title: "Demo" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
s.addText("One rogue agent in a fleet of five", { placeholder: "title" });
const agents = ["invoice-bot", "deploy-bot", "payroll-sync-bot", "governor (ours)", "hr-onboarding-bot"];
const scores = [90, 60, 10, 10, 0];
s.addChart(pres.charts.BAR, [{ name: "Risk score", labels: agents, values: scores }], {
  x: M, y: 1.55, w: 6.7, h: 4.9, barDir: "bar", objectName: "fleet-chart",
  chartColors: [HEX.accent2, HEX.accent3, HEX.accent4, HEX.accent4, HEX.accent1],
  catAxisOrientation: "maxMin", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisHidden: true,
  valGridLine: { style: "none" }, catGridLine: { style: "none" },
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
  catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt", catAxisLineShow: false,
  showLegend: false, showTitle: true, title: "Risk score (0-100)", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
  barGapWidthPct: 60,
});
card(s, 7.75, 1.55, 4.98, 4.9, "FDECEC");
s.addText([{ text: "invoice-bot", options: { bold: true, color: C.text1, fontSize: 22 } }], { x: 8.05, y: 1.8, w: 4.4, h: 0.5, margin: 0, isTextBox: true, fontFace: "Cambria", objectName: "ib-name" });
s.addText([{ text: "90", options: { bold: true, fontSize: 48, color: C.accent2 } }, { text: "  CRITICAL", options: { bold: true, fontSize: 18, color: C.accent2 } }],
  { x: 8.05, y: 2.3, w: 4.4, h: 0.95, valign: "middle", margin: 0, isTextBox: true, objectName: "ib-score" });
s.addText([
  { text: "+40  Owner Denise.Hunt is an inactive leaver", options: { bullet: false, breakLine: true } },
  { text: "+30  Violates ENFORCED SoD policy (matched by entitlement ID)", options: { breakLine: true } },
  { text: "+20  AccountsReceivable is outside its declared purpose", options: {} },
], { x: 8.05, y: 3.35, w: 4.45, h: 1.7, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true, objectName: "ib-signals" });
s.addText([{ text: "Escalate to: ", options: { bold: true } }, { text: "Catherine.Simmons, the departed owner's manager" }],
  { x: 8.05, y: 4.85, w: 4.45, h: 0.8, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "ib-escalate" });
s.addText("Agents are staged on a CSV source. Their owners, leaver status, entitlements and SoD policy are real ISC objects.",
  { x: M, y: 6.55, w: 12.1, h: 0.35, fontSize: 12, italic: true, color: C.accent4, margin: 0, isTextBox: true, objectName: "staged" });
s.addNotes("SAI (0:55-1:30): Are any of our agents rogue? invoice-bot is 90, critical. Its owner left, it holds access beyond its purpose, and it violates a real enforced SoD policy. Note hr-onboarding-bot at zero: the tool separates healthy agents from rogue ones, so you don't get alert fatigue. ALEX (1:30-1:55): Why does it have AccountsReceivable? Direct grant, no role justifies it, outside its declared purpose. IF ASKED about weights: deliberately simple and explainable; no accountable human (40) outranks a toxic access combination (30), which outranks drift (20); tunable in one place and unit-tested. IF ASKED about declaredAccess being self-declared: true; phase 2 sources purpose from the approved access request. The SoD and orphaned-owner checks fire regardless.");

// ---------- 6. Containment ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
s.addText("Nothing is contained until a human approves", { placeholder: "title" });
const flow = [
  { h: "Detect", d: "invoice-bot scores 90 CRITICAL", c: C.accent2 },
  { h: "Dry-run plan", d: "4 steps shown. Nothing changes.", c: C.accent4 },
  { h: "Human approves", d: "confirm=true with the dry-run token and a reason", c: C.accent3 },
  { h: "Contain", d: "Disable it in the target app; tag AGENT_QUARANTINED in ISC", c: C.accent1 },
  { h: "Escalate", d: "Route to the owner's manager for a new accountable owner", c: C.accent5 },
];
const fw = 2.2, fg = 0.28;
flow.forEach((f, i) => {
  const x = M + i * (fw + fg);
  card(s, x, 1.65, fw, 2.75);
  circleNum(s, x + 0.2, 1.85, i + 1, f.c);
  s.addText(f.h, { x: x + 0.2, y: 2.55, w: fw - 0.4, h: 0.5, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: id("flowh") });
  s.addText(f.d, { x: x + 0.2, y: 3.05, w: fw - 0.35, h: 1.25, fontSize: 14, color: C.text2, valign: "top", margin: 0, isTextBox: true, objectName: id("flowd") });
  if (i < flow.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + fw + 0.04, y: 2.9, w: 0.2, h: 0.26, fill: { color: C.accent4 }, line: { color: C.accent4, width: 0 }, objectName: id("farrow") });
});
s.addText("Guardrails", { x: M, y: 4.75, w: 4, h: 0.45, fontSize: 18, bold: true, color: C.text1, margin: 0, isTextBox: true, objectName: "guard-h" });
const guards = [
  ["4 of 5 tools read-only", "quarantine_agent is marked destructive; the server refuses to act without a dry-run token"],
  ["No secrets on disk", "Credentials live only in macOS Keychain or Windows Credential Manager"],
  ["Auditable and reversible", "Every ISC call logged with a correlation ID; one command reverses containment"],
];
guards.forEach((g, i) => {
  const x = M + i * 4.1;
  s.addText([{ text: g[0], options: { bold: true, color: C.text1, breakLine: true } }, { text: g[1], options: { color: C.text2 } }],
    { x, y: 5.25, w: 3.85, h: 1.2, fontSize: 14, valign: "top", margin: 0, isTextBox: true, objectName: id("guard") });
});
s.addNotes("SAI (1:55-2:40): Quarantine invoice-bot. It returns a plan and a one-time token, and changes nothing. The server refuses to act without that token. Confirmed: now it tags the agent in ISC and disables its account in the app it acts on, then escalates to Denise's manager. Re-run detection: QUARANTINED. If asked: the agents are staged; the owners, leaver status, entitlements and SoD policy are real. Flat-file sources can't provision, which we found in rehearsal, so we tag in ISC and disable at the target app. IF ASKED 'a tag isn't containment': correct, the disable in the target app stops the bot; the ISC tag is the governance record. IF ASKED about prompt injection through agent metadata: the model can plan, but only a human's confirm=true acts, after a dry run, and it is reversible. IF ASKED about sp:scopes:all: the lab requires it; production uses a read-only client plus one scoped write for tagging.");

// ---------- 7. Close ----------
pres.addSection({ title: "Close" });
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
s.addText("Your dashboards say green.", { placeholder: "title" });
s.addText("Ask the agent what they're not telling you.", { placeholder: "body" });
const vals = [
  ["One conversation", "Detect, explain and contain; each tool call takes under 5 seconds"],
  ["One model", "The same chain logic catches rogue agents and leavers"],
  ["30-day pilot", "Every CRITICAL agent contained within 1 business day"],
];
vals.forEach((v, i) => {
  const x = M + i * 4.1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.55, w: 3.85, h: 1.35, rectRadius: 0.12, fill: { color: "16233A" }, line: { color: "16233A", width: 0 }, objectName: id("valcard") });
  s.addText([{ text: v[0], options: { bold: true, fontSize: 20, color: C.accent1, breakLine: true } }, { text: v[1], options: { fontSize: 14, color: "C7D0DC" } }],
    { x: x + 0.25, y: 4.6, w: 3.4, h: 1.25, valign: "middle", margin: 0, isTextBox: true, objectName: id("valtxt") });
});
s.addText("github.com/sairavula/Sailpoint-Navigate26-HackDay", { x: M, y: 6.45, w: 8, h: 0.4, fontSize: 15, color: "93A1B5", margin: 0, isTextBox: true, objectName: "repo",
  hyperlink: { url: "https://github.com/sairavula/Sailpoint-Navigate26-HackDay" } });
s.addNotes("MUYIWA (2:40-3:00): Detection to containment in minutes, not days, and a human always approves. The same chain model covers people and agents. Next is a 30-day pilot. The code, tests and honest limitations are in the repo. Your dashboards say green; ask the agent what they're not telling you.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
