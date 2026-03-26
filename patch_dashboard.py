"""Patch dashboard.html with Google Sheets integration code."""
import re

with open(r'c:\Users\bryan\projects\Finance\dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Replace the RAW DATA header with SHEETS_CONFIG + RAW DATA header ────────
# Find the exact position of the <script> tag followed by the RAW DATA comment
script_pos = content.find('<script>\n// \u2500\u2500\u2500 RAW DATA ')
if script_pos == -1:
    print('ERROR: could not find RAW DATA comment in <script> block')
    exit(1)

eol = content.find('\n', script_pos + 10)          # end of the RAW DATA comment line
old_raw_header = content[script_pos:eol]

sheets_config_block = (
    '<script>\n'
    '// \u2550\u2550\u2550 GOOGLE SHEETS CONFIG \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n'
    '// Paste your values below. Sheet must be shared \u201cAnyone with the link can view\u201d.\n'
    "const SHEETS_CONFIG = {\n"
    "  apiKey:  'PASTE_YOUR_API_KEY_HERE',   // Google Cloud Console \u2192 APIs & Services \u2192 Credentials\n"
    "  sheetId: 'PASTE_YOUR_SHEET_ID_HERE',  // From your Sheets URL: /spreadsheets/d/XXXXX/edit\n"
    '};\n'
    '\n'
    '// \u2550\u2550\u2550 RAW DATA (fallback defaults \u2014 overwritten when Sheets loads) \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550'
)

content = content[:script_pos] + sheets_config_block + content[eol:]
print('Step 1 done: inserted SHEETS_CONFIG block')

# ── 2. Insert parseNum + loadFromSheets + bootstrap BEFORE initDashboard ───────
init_pos = content.find('function initDashboard()')
bootstrap_pos = content.find('(async () => {')

if init_pos == -1:
    print('ERROR: cannot find initDashboard()')
    exit(1)

if bootstrap_pos != -1:
    print('Step 2 skipped: loader+bootstrap already present')
else:
    loader_code = 
// ─── GOOGLE SHEETS LOADER ──────────────────────────────────────────────────────
function parseNum(v) {
  if (!v && v !== 0) return 0;
  const s = String(v).replace(/[$,\s]/g, '');
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

  // ─ Parse Cost sheet ─
  // Row 0 = headers; rows 1-4 = fiscal-year rows ("2025-26" … "2022-23").
  // User deleted rows 8-11 (numeric duplicates) in Google Sheets.
  const cRows = (cRes.values || []).filter(r => r[0] && r[1] && /^\d{4}-\d{2}$/.test(String(r[0]).trim()));
  const yearMap = { '2025-26': 2025, '2024-25': 2024, '2023-24': 2023, '2022-23': 2022 };

  const newCosts = {};
  cRows.forEach(r => {
    const yr = yearMap[String(r[0]).trim()];
    if (yr) newCosts[yr] = parseNum(r[1]);
  });

  // NIL Revenue Share → column AK (index 36) from 2025-26 row
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

  // ─ Parse Revenue sheet ─
  // Row 0 = headers; data rows have a 4-digit fiscal year in column A.
  const rRows  = (rRes.values || []).filter(r => r[0] && /^\d{4}$/.test(String(r[0]).trim()));
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

// ─── BOOTSTRAP ─────────────────────────────────────────────────────────────────
(async () => {
  const overlay    = document.getElementById('loadingOverlay');
  const badge      = document.getElementById('dataSourceBadge');
  const configured = SHEETS_CONFIG.apiKey  !== 'PASTE_YOUR_API_KEY_HERE' &&
                     SHEETS_CONFIG.sheetId !== 'PASTE_YOUR_SHEET_ID_HERE';

  if (configured) {
    overlay.style.display = 'flex';
    try {
      const d = await loadFromSheets();
      Object.keys(d.newCosts).forEach(yr   => { costs[yr]        = d.newCosts[yr]; });
      Object.keys(d.newRevenue).forEach(yr => { revenue[yr]      = d.newRevenue[yr]; });
      Object.keys(d.newRevMix).forEach(lbl => { revMix2025[lbl]  = d.newRevMix[lbl]; });
      NIL_BASE = d.newNIL;
      topExpenses2024.length = 0;
      topExpenses2024.push(...d.newTopExp);
      badge.textContent = '\u25cf Live \u2014 Google Sheets';
      badge.style.display = 'inline-flex';
    } catch (err) {
      console.warn('Google Sheets load failed \u2014 using hardcoded data:', err);
      badge.textContent = '\u26a0 Sheets offline \u2014 showing cached data';
      badge.classList.add('error');
      badge.style.display = 'inline-flex';
    }
    overlay.style.display = 'none';
  }

  initDashboard();
})();

"""
    # Re-find init_pos after step 1 changed the content
    init_pos = content.find('function initDashboard()')
    content = content[:init_pos] + loader_code + content[init_pos:]
    print('Step 2 done: inserted loader + bootstrap before initDashboard')

with open(r'c:\Users\bryan\projects\Finance\dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('File written OK')

# Verify
with open(r'c:\Users\bryan\projects\Finance\dashboard.html', 'r', encoding='utf-8') as f:
    verify = f.read()
print('SHEETS_CONFIG present:', 'SHEETS_CONFIG' in verify)
print('loadFromSheets present:', 'loadFromSheets' in verify)
print('parseNum present:', 'parseNum' in verify)
print('initDashboard present:', 'initDashboard' in verify)
print('async bootstrap present:', '(async () => {' in verify)
