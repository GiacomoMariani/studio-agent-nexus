"""Design-system CSS for Studio Agent Nexus.

Ported from the design prototype: dark-navy shell, amber accent, white content
panels, Inter typography. Aggressive Streamlit overrides are used deliberately to match
the prototype (approved design-fidelity trade-off).
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    /* Surfaces */
    --bg:            #0F172A;
    --bg-2:          #1E293B;
    --bg-3:          #334155;
    --surface:       #FFFFFF;
    --surface-muted: #F8FAFC;

    /* Accent */
    --accent:        #F59E0B;
    --accent-warm:   #FBBF24;
    --accent-dim:    #78350F;

    /* Text */
    --text-on-dark:        #F1F5F9;
    --text-muted-on-dark:  #94A3B8;
    --text-on-light:       #0F172A;
    --text-muted-on-light: #64748B;
    --text-faint:          #475569;

    /* Lines */
    --line-dark:  #334155;
    --line-light: #E5E7EB;

    /* Semantic */
    --success: #22C55E;
    --warning: #F59E0B;
    --error:   #EF4444;
    --info:    #3B82F6;

    /* Department (multiplayer-backend taxonomy) */
    --dept-backend:    #3B82F6;
    --dept-infra:      #8B5CF6;
    --dept-data:       #6366F1;
    --dept-qa:         #F97316;
    --dept-production: #14B8A6;

    /* Priority */
    --pri-critical: #EF4444;
    --pri-high:     #F97316;
    --pri-medium:   #F59E0B;
    --pri-low:      #22C55E;

    /* Spacing (4px scale) */
    --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
    --sp-5: 20px; --sp-6: 24px; --sp-8: 32px; --sp-10: 40px; --sp-12: 48px;

    /* Type */
    --font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', ui-monospace, monospace;
    --fs-display: 2.25rem;
    --fs-h1: 1.5rem;
    --fs-h2: 1.125rem;
    --fs-body: 0.9375rem;
    --fs-small: 0.8125rem;
    --fs-caption: 0.75rem;

    --radius-card: 12px;
    --radius-btn: 8px;
}

/* ---- Global shell ---- */
html, body, [class*="css"] { font-family: var(--font); }
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg); }
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stMainBlockContainer"], .block-container {
    padding-top: 2rem; padding-bottom: 3rem; max-width: 1100px;
}
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: var(--bg); border-right: 1px solid var(--line-dark); width: 248px !important;
}
[data-testid="stSidebar"] > div { padding-top: var(--sp-5); }

.wordmark__row { display: flex; align-items: center; gap: var(--sp-3); }
.wordmark__mark {
    width: 28px; height: 28px; border-radius: 7px; background: var(--accent);
    display: flex; align-items: center; justify-content: center; flex: 0 0 auto;
}
.wordmark__title { font-weight: 700; font-size: 1.0rem; color: var(--text-on-dark); }
.wordmark__title .nexus { color: var(--accent); }
.wordmark__sub {
    color: var(--text-muted-on-dark); font-size: var(--fs-caption);
    margin-top: 4px; margin-left: 40px; letter-spacing: .01em;
}
.sidebar-divider { border-top: 1px solid var(--line-dark); margin: var(--sp-4) 0; }
.sidebar-label {
    color: var(--text-muted-on-dark); font-size: 0.625rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em; margin-bottom: var(--sp-2);
}
.sidebar-credit {
    color: var(--text-faint); font-size: var(--fs-caption); margin-top: var(--sp-5);
}

/* Nav buttons (active = primary, inactive = secondary) */
[data-testid="stSidebar"] .stButton > button {
    width: 100%; justify-content: flex-start; text-align: left;
    border-radius: var(--radius-btn); font-weight: 600; font-size: var(--fs-body);
    padding: 0.55rem 0.7rem; border: 1px solid transparent; margin-bottom: 2px;
    background: transparent; color: var(--text-muted-on-dark);
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-2); color: var(--text-on-dark); border-color: transparent;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: var(--bg-2); color: var(--accent);
    border-left: 3px solid var(--accent); box-shadow: none;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: var(--bg-2); color: var(--accent);
}

/* ---- Buttons (main area) ---- */
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background: var(--accent); color: var(--text-on-light); font-weight: 700;
    border: none; border-radius: var(--radius-btn);
}
.stButton > button[kind="primary"]:hover { background: var(--accent-warm); color: var(--text-on-light); }

/* ---- Inputs ---- */
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: var(--bg-2); color: var(--text-on-dark); border-color: var(--line-dark);
}

/* ---- Page header ---- */
.page-header { margin-bottom: var(--sp-6); }
.page-header__title {
    font-size: var(--fs-display); font-weight: 700; color: var(--text-on-dark);
    line-height: 1.1; letter-spacing: -0.02em; margin: 0;
}
.page-header__sub {
    color: var(--text-muted-on-dark); font-size: var(--fs-body);
    margin-top: var(--sp-2); max-width: 680px;
}

/* ---- Cards ---- */
.card {
    background: var(--surface); border: 1px solid var(--line-light);
    border-radius: var(--radius-card); padding: var(--sp-5);
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.dcard {
    background: var(--bg-2); border: 1px solid var(--line-dark);
    border-radius: var(--radius-card); padding: var(--sp-6);
}
.accent-top { border-top: 3px solid var(--accent); }
.stats-line { color: var(--text-muted-on-dark); font-size: var(--fs-small); }
.muted-caption { color: var(--text-muted-on-dark); font-size: var(--fs-caption); }
.kicker {
    color: var(--text-muted-on-dark); font-size: 0.625rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em;
}

/* ---- Badges ---- */
.badge {
    display: inline-flex; align-items: center; gap: 4px; padding: 0.2rem 0.55rem;
    border-radius: 999px; font-size: var(--fs-caption); font-weight: 600; line-height: 1.4;
}
.badge--dept { color: #fff; }
.badge--backend    { background: var(--dept-backend); color:#fff; }
.badge--infra      { background: var(--dept-infra); color:#fff; }
.badge--data       { background: var(--dept-data); color:#fff; }
.badge--qa         { background: var(--dept-qa); color:#fff; }
.badge--production  { background: var(--dept-production); color:#fff; }
.badge--critical { background: var(--pri-critical); color:#fff; }
.badge--high     { background: var(--pri-high); color:#fff; }
.badge--medium   { background: var(--pri-medium); color: var(--text-on-light); }
.badge--low      { background: var(--pri-low); color: var(--text-on-light); }
.badge--type-md  { background: rgba(59,130,246,.15); color: var(--info); }
.badge--type-pdf { background: rgba(139,92,246,.15); color: var(--dept-production); }
.badge--mode-openai { background: rgba(59,130,246,.15); color: var(--info); }
.badge--mode-gemini { background: rgba(138,180,248,.18); color:#8ab4f8; }
.badge--mode-groq   { background: rgba(240,101,67,.18); color:#f06543; }
.badge--mode-local  { background: var(--bg-3); color: var(--text-muted-on-dark); }
.badge--status-indexed    { background: rgba(34,197,94,.15); color: var(--success); }
.badge--status-processing { background: rgba(245,158,11,.15); color: var(--accent); }
.badge--status-failed     { background: rgba(239,68,68,.15); color: var(--error); }

/* Skill badge ("What this page demonstrates") */
.skill-badge {
    display: inline-block; background: var(--bg); border: 1px solid var(--accent);
    color: var(--accent); font-size: 0.7rem; font-weight: 600; letter-spacing: .04em;
    text-transform: uppercase; padding: 0.25rem 0.55rem; border-radius: 999px;
    margin: 0 var(--sp-2) var(--sp-2) 0;
}

/* Fallback notice */
.fallback {
    background: rgba(245,158,11,0.08); border: 1px solid var(--accent);
    border-radius: var(--radius-card); padding: var(--sp-5);
    display: flex; gap: var(--sp-4); align-items: flex-start;
}
.fallback__title { font-weight: 700; color: var(--accent-warm); font-size: 0.95rem; }
.fallback__sub { color: var(--text-muted-on-dark); font-size: var(--fs-small); margin-top: 2px; }

/* Stat card */
.stat-card { background: var(--bg-2); border: 1px solid var(--line-dark);
    border-radius: var(--radius-card); padding: var(--sp-5); }
.stat-card__value { font-size: 2.1rem; font-weight: 700; line-height: 1.1;
    letter-spacing: -0.02em; margin-top: 6px; }
.stat-card__value--white { color: var(--text-on-dark); }
.stat-card__value--amber { color: var(--accent); }
.stat-card__value--red { color: #F87171; }
.stat-card__value--green { color: #4ADE80; }

/* Placeholder */
.placeholder {
    background: var(--bg-2); border: 1px dashed var(--line-dark);
    border-radius: var(--radius-card); padding: var(--sp-10); text-align: center;
    color: var(--text-muted-on-dark);
}

/* Footer "what this demonstrates" */
.footer-text { color: var(--text-muted-on-dark); font-size: var(--fs-body); line-height: 1.65; }
</style>
"""
