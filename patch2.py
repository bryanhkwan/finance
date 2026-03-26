"""Patch dashboard.html: add SHEETS_CONFIG and replace INIT block."""

with open(r'c:\Users\bryan\projects\Finance\dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── Quick guard ────────────────────────────────────────────────────────────────
already_done = 'SHEETS_CONFIG' in content and 'loadFromSheets' in content
if already_done:
    print('Already patched — nothing to do.')
    exit(0)

# ═══════════════════════════════════════════════════════════════════════════════
# PART A — Insert SHEETS_CONFIG block right after <script> tag
# ═══════════════════════════════════════════════════════════════════════════════
# The script tag is followed immediately by the RAW DATA comment line.
# Strategy: find <script>\n then insert the config before the existing comment.

SCRIPT_TAG = '<script>\n'
script_pos  = content.find(SCRIPT_TAG + '//')   # '<script>\n//'
if script_pos == -1:
    print('ERROR: cannot find <script> + comment start')
    exit(1)

insert_at = script_pos + len(SCRIPT_TAG)   # position right after the newline

config_block = (
    "// \u2500\u2500\u2500 GOOGLE SHEETS CONFIG \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
    "// Paste your values. Sheet must be shared \u201cAnyone with the link can view\u201d.\n"
    "const SHEETS_CONFIG = {\n"
    "  apiKey:  'PASTE_YOUR_API_KEY_HERE',   // Google Cloud Console \u2192 Credentials\n"
    "  sheetId: 'PASTE_YOUR_SHEET_ID_HERE',  // docs.google.com/spreadsheets/d/XXXXX/edit\n"
    "};\n\n"
)

content = content[:insert_at] + config_block + content[insert_at:]
print('Part A done: SHEETS_CONFIG inserted')

# ═══════════════════════════════════════════════════════════════════════════════
# PART B — Replace bare INIT block with initDashboard() + loader + bootstrap
# ═══════════════════════════════════════════════════════════════════════════════
# The INIT block starts at "// --- INIT ---" and ends after "updateRatioCalc(30);"

INIT_MARKER  = '// \u2500\u2500\u2500 INIT '
END_OF_INIT  = 'updateRatioCalc(30);'

init_start = content.find(INIT_MARKER)
if init_start == -1:
    print('ERROR: cannot find INIT marker')
    exit(1)

end_idx = content.find(END_OF_INIT, init_start)
if end_idx == -1:
    print('ERROR: cannot find end of INIT block')
    exit(1)

end_idx += len(END_OF_INIT)   # include the statement itself

new_block = """// \u2500\u2500\u2500 GOOGLE SHEETS LOADER \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function parseNum(v) {
  if (!v && v !== 0) return 0;
  const s = String(v).replace(/[$,\\s]/g, '');
  if (s.endsWith('M')) return parseFloat(s) * 1e6;
  if (s.endsWith('K')) return parseFloat(s) * 1e3;
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}

async function loadFromSheets() {
  const base = `https://sheets.googleapis.com/v4/spreadsheets/${SHEETS_CONFIG.sheetId}/values`;
  const k    = `key=${SHEETS_CONFIG.apiKey}`;

  const [cRes, rRes] = await Promise.all([
    fetch(`${base}/Cost!A1:AK8?${k}`).then(r => { if (!r.ok) throw new Error('Cost ' + r.status); return r.json(); }),
    fetch(`${base}/Revenue!A1:K8?${k}`).then(r => { if (!r.ok) throw new Error('Revenue ' + r.status); return r.json(); }),
  ]);

  // Cost sheet: row 0 = headers, rows 1-4 = "2025-26" through "2022-23" fiscal year data.
  const cRows   = (cRes.values || []).filter(r => r[0] && r[1] && /^\\d{4}-\\d{2}$/.test(String(r[0]).trim()));
  const yearMap = { '2025-26': 2025, '2024-25': 2024, '2023-24': 2023, '2022-23': 2022 };

  const newCosts = {};
  cRows.forEach(r => {
    const yr = yearMap[String(r[0]).trim()];
    if (yr) newCosts[yr] = parseNum(r[1]);
  });

  // Column AK (index 36) = NIL Revenue Share from 2025-26 row
  const row2025cost = cRows.find(r => String(r[0]).trim() === '2025-26') || [];
  const newNIL      = parseNum(row2025cost[36]) || NIL_BASE;

  // Top expense categories from 2024-25 row
  const row2024cost = cRows.find(r => String(r[0]).trim() === '2024-25') || [];
  const newTopExp = [
    { name: 'Admin Salaries',          value: parseNum(row2024cost[9])  },
    { name: 'Head Coaches',            value: parseNum(row2024cost[20]) },
    { name: 'Student Aid',             value: parseNum(row2024cost[2])  },
    { name: 'Total Coaches (pkg)',     value: parseNum(row2024cost[5])  },
    { name: 'Travel',                  value: parseNum(row2024cost[6])  },
    { name: 'Other / Alston Benefits', value: parseNum(row2024cost[35]) },
    { name: 'Recruiting',              value: parseNum(row2024cost[3])  },
    { name: 'Marketing',               value: parseNum(row2024cost[4])  },
    { name: 'Equipment',               value: parseNum(row2024cost[12]) },
    { name: 'NIL Revenue Share',       value: newNIL },
  ];

  // Revenue sheet: row 0 = headers, data rows have 4-digit year in col A (2025, 2024, …)
  const rRows  = (rRes.values || []).filter(r => r[0] && /^\\d{4}$/.test(String(r[0]).trim()));
  const newRevenue = {};
  const newRevMix  = {};
  const revLabels  = [
    'Ticket Sales', 'Guarantees', 'Fundraising', 'Media Rights',
    'NCAA Distributions', 'Conference Distributions', 'Concessions/Novelty',
    'Sponsorships/Royalties', 'Endowment & Investments',
  ];

  rRows.forEach(r => {
    const yr  = parseInt(r[0]);
    const tot = parseNum(r[10]) || revLabels.reduce((s, _, i) => s + parseNum(r[i + 1]), 0);
    newRevenue[yr] = tot;
    if (yr === 2025) revLabels.forEach((lbl, i) => { newRevMix[lbl] = parseNum(r[i + 1]); });
  });

  return { newCosts, newRevenue, newRevMix, newNIL, newTopExp };
}

// \u2500\u2500\u2500 INIT \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function initDashboard() {
  // Re-compute OLS now that data is finalised
  olsExpForecast = linearForecast(costs, forecastYears);
  olsRevForecast = linearForecast(revenue, forecastYears);

  // Keep the Rev Share Investment Planner object in sync with live data
  RC.baseRS    = NIL_BASE;
  RC.nonRS     = costs[2025] - NIL_BASE;
  RC.baseExp   = costs[2025];
  RC.baseRev   = revenue[2025];
  RC.baseRatio = costs[2025] / revenue[2025];
  RC.cap       = HOUSE_CAP_2025;

  renderKPIs();
  buildSliders();
  buildOverviewChart();
  buildYoyChart();
  buildScenarioChart();
  buildRevMixChart();
  renderForecastTable();
  renderExpBreakdown();
  buildScenarioTable();
  updateRatioCalc(30);
}

// \u2500\u2500\u2500 BOOTSTRAP \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
(async () => {
  const overlay    = document.getElementById('loadingOverlay');
  const badge      = document.getElementById('dataSourceBadge');
  const configured = SHEETS_CONFIG.apiKey  !== 'PASTE_YOUR_API_KEY_HERE' &&
                     SHEETS_CONFIG.sheetId !== 'PASTE_YOUR_SHEET_ID_HERE';

  if (configured) {
    overlay.style.display = 'flex';
    try {
      const d = await loadFromSheets();
      Object.keys(d.newCosts).forEach(yr    => { costs[yr]       = d.newCosts[yr]; });
      Object.keys(d.newRevenue).forEach(yr  => { revenue[yr]     = d.newRevenue[yr]; });
      Object.keys(d.newRevMix).forEach(lbl  => { revMix2025[lbl] = d.newRevMix[lbl]; });
      NIL_BASE = d.newNIL;
      topExpenses2024.length = 0;
      topExpenses2024.push(...d.newTopExp);
      badge.textContent = '\\u25cf Live \\u2014 Google Sheets';
      badge.style.display = 'inline-flex';
    } catch (err) {
      console.warn('Google Sheets load failed \\u2014 using hardcoded data:', err);
      badge.textContent = '\\u26a0 Sheets offline \\u2014 showing cached data';
      badge.classList.add('error');
      badge.style.display = 'inline-flex';
    }
    overlay.style.display = 'none';
  }

  initDashboard();
})();"""

content = content[:init_start] + new_block + content[end_idx:]
print('Part B done: INIT block replaced with initDashboard + loader + bootstrap')

# ═══════════════════════════════════════════════════════════════════════════════
# Write & verify
# ═══════════════════════════════════════════════════════════════════════════════
with open(r'c:\Users\bryan\projects\Finance\dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open(r'c:\Users\bryan\projects\Finance\dashboard.html', 'r', encoding='utf-8') as f:
    v = f.read()

print()
print('Verification:')
print('  SHEETS_CONFIG    :', 'SHEETS_CONFIG' in v)
print('  parseNum         :', 'parseNum' in v)
print('  loadFromSheets   :', 'loadFromSheets' in v)
print('  initDashboard    :', 'function initDashboard' in v)
print('  async bootstrap  :', '(async () => {' in v)
print('  loading overlay  :', 'loadingOverlay' in v)
print('  dataSrcBadge     :', 'dataSourceBadge' in v)
