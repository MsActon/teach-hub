# Teach Hub — Full App (Layout v1 + Expanded Content + Droichead + Teacher Challenges)
# Single-file Streamlit app (Thonny/Windows friendly)
# ✅ Adds Teacher Challenges (daily log + streaks + reflections) using SQLite
# ✅ Uses existing “nickname” as the user identity (no full login yet, so it stays simple)

import os
import re
import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple

import streamlit as st

# ----------------------------
# FILES / BRANDING
# ----------------------------
LOGO_FILE = "teachhub_logo.png"   # put this in same folder as app.py

# Favicon/tab icon (optional included) — safe fallback to emoji if file missing
PAGE_ICON = LOGO_FILE if os.path.exists(LOGO_FILE) else "🧑‍🏫"

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Teach Hub",
    page_icon=PAGE_ICON,
    layout="wide"
)

DB_FILE = "teachhub.db"

EAS_URL = (
    "https://www.gov.ie/en/department-of-education/services/"
    "employee-assistance-service-for-school-staff-in-recognised-primary-and-post-primary-schools/"
)

DROICHEAD_URL = "https://www.teachingcouncil.ie/i-am-a-registered-teacher/registration-with-conditions/droichead/"

# ----------------------------
# HELPERS (must be above sidebar usage)
# ----------------------------
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def clean_nickname(n: str) -> str:
    """Keep nickname simple, safe and short."""
    n = (n or "").strip()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"[^a-zA-Z0-9 _-]", "", n)
    return n[:20]


def show_logo(where: str, width: Optional[int] = None):
    """
    Optional logo display with safe fallback.
    where: "sidebar" or "main"
    """
    if os.path.exists(LOGO_FILE):
        if where == "sidebar":
            st.sidebar.image(LOGO_FILE, use_container_width=True)
        else:
            if width:
                st.image(LOGO_FILE, width=width)
            else:
                st.image(LOGO_FILE, use_container_width=False)
    else:
        # No crash if missing; gentle hint only once.
        if "logo_warned" not in st.session_state:
            st.session_state.logo_warned = True
            st.sidebar.info(f"Tip: put **{LOGO_FILE}** beside app.py to enable branding.")

# ----------------------------
# DATABASE
# ----------------------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Community tables
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
        """
    )

    # Teacher Challenges tables
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            instruction TEXT NOT NULL,
            seconds INTEGER NOT NULL DEFAULT 60
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS challenge_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            author TEXT NOT NULL,
            challenge_code TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(log_date, author, challenge_code)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            author TEXT NOT NULL,
            win TEXT,
            stress_shift TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(log_date, author)
        )
        """
    )

    # Seed default challenges (safe to run repeatedly)
    default_challenges = [
        ("CHALLENGE_MINDSET", "Challenge mindset", "Stress → Performance",
         "Pick ONE moment today to reframe as a challenge (not a threat). Say: “I’m excited” or “This is practice.”", 60),
        ("BREATH_RESET", "30-second breathing reset", "Stress → Performance",
         "Breathe in for 5, out for 5 (or 6) for 3 cycles. Use before meetings/classes.", 45),
        ("SMALL_GOAL", "Small goal (finishable)", "Momentum",
         "Write ONE small task you will finish today. When done, take 2 minutes to enjoy the win.", 90),
        ("MOVE_10", "10-minute brisk walk", "Brain boost",
         "Move for 10 minutes (walk counts). Outdoor if possible. Aim to reset your head, not smash a workout.", 600),
        ("SINGLE_TASK", "Single-task focus", "Workload",
         "Turn off notifications for 20 minutes and do ONE thing properly.", 1200),
        ("POSTURE_CHECK", "Posture check", "Energy",
         "Sit tall / shoulders open for 60 seconds. Head up. Reset your state.", 60),
        ("RIGHT_HAND_SQUEEZE", "Right-hand squeeze", "Confidence",
         "Squeeze your right hand firmly for ~45 seconds before a stressful moment (call / presentation).", 45),
        ("PAUSE_BETWEEN", "Pause between tasks", "Attention",
         "Take a 2–5 minute pause between tasks (breathing / stretch / short reset) instead of rushing.", 180),
    ]

    for code, title, category, instruction, seconds in default_challenges:
        cur.execute(
            """
            INSERT OR IGNORE INTO challenges (code, title, category, instruction, seconds)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, title, category, instruction, seconds),
        )

    conn.commit()
    conn.close()


init_db()

# ----------------------------
# CONTENT
# ----------------------------
COMMUNITY_CATEGORIES = [
    "Behaviour & classroom management",
    "Project work support",
    "SEN / inclusion",
    "Assessment & reporting",
    "Workload hacks",
    "Pay, leave & entitlements",
    "NQT questions",
    "Wellbeing & balance",
    "Other",
]

SUPPORT_LINKS = [
    {
        "name": "ASTI (Association of Secondary Teachers, Ireland)",
        "desc": "Union supports, guidance, advice, representation.",
        "url": "https://www.asti.ie/",
    },
    {
        "name": "TUI (Teachers' Union of Ireland)",
        "desc": "Union supports, guidance, advice, representation.",
        "url": "https://www.tui.ie/",
    },
    {
        "name": "Employee Assistance Service (EAS) — Dept of Education",
        "desc": "Confidential support service for school staff (Ireland).",
        "url": EAS_URL,
    },
    {
        "name": "Teaching Council",
        "desc": "Teacher registration, standards, professional learning info.",
        "url": "https://www.teachingcouncil.ie/",
    },
    {
        "name": "Teaching Council — Droichead",
        "desc": "Guidance on Droichead (NQT induction) and registration with conditions.",
        "url": DROICHEAD_URL,
    },
    {
        "name": "Oide (Professional Learning Supports)",
        "desc": "Professional learning supports for teachers (Ireland).",
        "url": "https://oide.ie/",
    },
]

# Pay/Leave/Tax content
PAYSLIP_POINTS = [
    "**Gross Pay**: Salary before deductions.",
    "**Net Pay**: What lands in your bank after deductions.",
    "**PAYE**: Income tax deducted through payroll.",
    "**USC**: Universal Social Charge (banded tax).",
    "**PRSI**: Social insurance (benefits e.g., illness, maternity, pension).",
    "**Pension / Superannuation**: Pension contributions (public service pension).",
    "**Additional payments** (if relevant): S&S, substitution, overtime, etc.",
    "**Tax credits / cut-off point**: Determines PAYE (set in Revenue).",
]

BIKE_TO_WORK_POINTS = [
    "Buy a bicycle / e-bike and safety gear through your employer.",
    "Usually paid through salary sacrifice over an agreed period (can reduce tax on that portion).",
    "Often available once per set period (commonly 4 years) — confirm current rules with Revenue/payroll.",
    "Ask your payroll what provider/process they use.",
]

FLAT_RATE_MEDICAL_POINTS = [
    "**Flat-rate expenses**: Standard amount against tax for qualifying roles/conditions (reduces taxable income).",
    "Usually claimed through Revenue online.",
    "**Medical expenses**: Keep receipts; many costs can be claimed back at standard rate through Revenue.",
    "Tip: keep a folder of receipts (photos work) throughout the year.",
]

SICK_LEAVE_POINTS = [
    "Notify the school as early as possible (follow local policy).",
    "Submit medical certs if required, promptly.",
    "Payroll/HR tracks sick leave and pay entitlements.",
    "If long-term: keep communication clear and ask for written confirmation of steps/forms.",
]

MATERNITY_POINTS = [
    "Apply early once dates are known; confirm paperwork route (school + payroll).",
    "Check how pay works for your contract type and required forms.",
    "Consider parent’s leave / parental leave timelines too.",
]

TAX_POINTS = [
    "PAYE: tax is deducted automatically based on your Revenue details.",
    "Review your Revenue account so tax credits and cut-off points are correct.",
    "If multiple employments (subbing + part-time), ensure credits are allocated appropriately.",
]

SUMMER_WELFARE_POINTS = [
    "If you don’t have a full contract, you may qualify for social welfare during summer/holiday periods.",
    "Apply as soon as term ends — delays can affect payment start dates.",
    "Have documents ready: contract details, payslips, and work pattern confirmation if asked.",
]

SCHOOL_STRUCTURES_POINTS = [
    "**Croke Park hours**: Additional annual hours outside timetabled teaching (meetings, planning, CPD, etc.).",
    "**S&S (Supervision & Substitution)**: supervision/yard duty + covering classes when needed.",
    "Ask for rota/policy early (especially as an NQT).",
]

# Classroom practice content
CLASSROOM_MGMT_POINTS = [
    "Build routines: entry, seating, materials, transitions, exit.",
    "Be consistent: same behaviour = same response.",
    "Use calm correction: name behaviour, state expectation, follow through.",
    "Praise specifically: describe the behaviour you want repeated.",
    "Follow the school’s policy pathway (referrals, notes, escalation).",
]

PROJECT_WORK_POINTS = [
    "Chunk deadlines: topic → question → method → data → analysis → write-up.",
    "Use exemplars + a checklist rubric so students know what quality looks like.",
    "Teach research basics explicitly: sources, bias, citations, data quality.",
    "Weekly progress log: what I did + next step.",
    "Mini-checkpoints: method approved → data verified → analysis checked.",
]

# NQT Hub + Droichead
NQT_SECTIONS = {
    "Droichead (NQT induction process)": [
        "Droichead is the main induction process for newly qualified teachers in Ireland.",
        "It supports NQTs through structured, school-based professional learning and support.",
        "In many schools, you’ll work with a Professional Support Team (PST).",
        "Keep evidence of progress (planning, reflections, feedback notes, assessment samples).",
        "Your school and Teaching Council guidance outline the steps and confirmations required.",
    ],
    "Contracts: the basics (high-level)": [
        "Fixed-term, part-time hours, and subbing are common early-career routes.",
        "CID is a route to longer-term security after meeting criteria — confirm with your union.",
        "Keep records: contract letters, timetables, payslips, written confirmation of hours/duties.",
        "If unsure: ask for clarification in writing to school/payroll/ETB.",
    ],
    "School types & roles": [
        "ETB / voluntary / community schools can differ in structures and payroll systems.",
        "Know roles: Principal/Deputy, Year Head, SEN/Inclusion team, post-holders, tutor.",
        "Ask early for: behaviour policy, SEN referral pathway, incident reporting steps, key contacts.",
    ],
    "Professional identity: Teaching Council": [
        "Registration and professional standards sit here.",
        "Keep your details updated and track requirements linked to your registration status.",
    ],
    "Further education & supports": [
        "Professional learning (Oide/CPD), EPV courses, postgraduate options, leadership pathways.",
        "Pick one purposeful goal per term (e.g., assessment, SEN strategies, classroom management).",
    ],
    "Practical school life: emails, meetings, boundaries": [
        "Use email templates; keep records of key communications.",
        "Bring a short agenda to meetings (what you need, what you’ve tried, next step).",
        "Set one sustainable boundary (cut-off time, batching correction, batching emails).",
    ],
    "Croke Park hours & S&S duty": [
        "Croke Park hours: meetings/CPD/whole-school work outside teaching contact time.",
        "S&S duty: supervision and substitution — ask for rota and expectations early.",
        "If unclear: ask for the policy/rota in writing.",
    ],
}

# ----------------------------
# COMMUNITY DB HELPERS
# ----------------------------
def require_nickname_or_stop():
    if st.session_state.nickname.strip() == "":
        st.warning("Please add a nickname in the sidebar to post, reply, or log challenges.")
        st.stop()


def add_post(author, category, title, body):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO posts (created_at, author, category, title, body) VALUES (?, ?, ?, ?, ?)",
        (now_str(), author, category, title.strip(), body.strip()),
    )
    conn.commit()
    conn.close()


def add_reply(post_id, author, body):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO replies (post_id, created_at, author, body) VALUES (?, ?, ?, ?)",
        (post_id, now_str(), author, body.strip()),
    )
    conn.commit()
    conn.close()


def fetch_posts(search_text="", category_filter="All"):
    conn = get_conn()
    cur = conn.cursor()

    query = "SELECT id, created_at, author, category, title, body FROM posts"
    params = []
    where = []

    if category_filter != "All":
        where.append("category = ?")
        params.append(category_filter)

    if search_text.strip():
        where.append("(title LIKE ? OR body LIKE ?)")
        s = f"%{search_text.strip()}%"
        params.extend([s, s])

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY id DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_replies(post_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT created_at, author, body FROM replies WHERE post_id = ? ORDER BY id ASC",
        (post_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ----------------------------
# CHALLENGES DB HELPERS
# ----------------------------
def fetch_challenges() -> List[Tuple[str, str, str, str, int]]:
    """Returns list of (code, title, category, instruction, seconds)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT code, title, category, instruction, seconds FROM challenges ORDER BY id ASC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def fetch_user_logs(author: str, log_date: str) -> Dict[str, int]:
    """Returns {challenge_code: completed} for a user on a given date."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT challenge_code, completed
        FROM challenge_logs
        WHERE author = ? AND log_date = ?
        """,
        (author, log_date),
    )
    rows = cur.fetchall()
    conn.close()
    return {code: int(done) for code, done in rows}


def set_challenge_completion(author: str, log_date: str, challenge_code: str, completed: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO challenge_logs (log_date, author, challenge_code, completed, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(log_date, author, challenge_code)
        DO UPDATE SET completed = excluded.completed, created_at = excluded.created_at
        """,
        (log_date, author, challenge_code, int(completed), now_str()),
    )
    conn.commit()
    conn.close()


def fetch_reflection(author: str, log_date: str) -> Dict[str, str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT win, stress_shift, note
        FROM daily_reflections
        WHERE author = ? AND log_date = ?
        """,
        (author, log_date),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"win": "", "stress_shift": "", "note": ""}
    return {"win": row[0] or "", "stress_shift": row[1] or "", "note": row[2] or ""}


def save_reflection(author: str, log_date: str, win: str, stress_shift: str, note: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO daily_reflections (log_date, author, win, stress_shift, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(log_date, author)
        DO UPDATE SET win = excluded.win, stress_shift = excluded.stress_shift, note = excluded.note, created_at = excluded.created_at
        """,
        (log_date, author, win.strip(), stress_shift.strip(), note.strip(), now_str()),
    )
    conn.commit()
    conn.close()


def compute_streak(author: str) -> int:
    """
    Streak = consecutive days up to today where user completed at least one challenge.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Get distinct dates where any completion happened
    cur.execute(
        """
        SELECT DISTINCT log_date
        FROM challenge_logs
        WHERE author = ? AND completed = 1
        """,
        (author,),
    )
    rows = cur.fetchall()
    conn.close()

    completed_dates = set(r[0] for r in rows)
    streak = 0
    d = date.today()
    while True:
        ds = d.strftime("%Y-%m-%d")
        if ds in completed_dates:
            streak += 1
            d = d - timedelta(days=1)
        else:
            break
    return streak


def completed_count_in_range(author: str, start_date: date, end_date: date) -> int:
    """Count completed logs between dates inclusive."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM challenge_logs
        WHERE author = ? AND completed = 1 AND log_date >= ? AND log_date <= ?
        """,
        (author, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
    )
    n = int(cur.fetchone()[0] or 0)
    conn.close()
    return n


def daily_completion_total(author: str, log_date: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM challenge_logs
        WHERE author = ? AND log_date = ? AND completed = 1
        """,
        (author, log_date),
    )
    n = int(cur.fetchone()[0] or 0)
    conn.close()
    return n


# ----------------------------
# WELLBEING (proper scaling)
# ----------------------------
def wellbeing_assessment(workload, exhaustion, sleep_problem, support_problem, boundary_problem):
    # All sliders: 1 = doing well, 10 = struggling
    score = (
        1.2 * workload
        + 1.4 * exhaustion
        + 1.0 * sleep_problem
        + 0.8 * support_problem
        + 0.6 * boundary_problem
    )
    if score >= 32:
        level = "Red"
    elif score >= 20:
        level = "Amber"
    else:
        level = "Green"
    return level, round(score, 1)


def advice_for_level(level):
    if level == "Green":
        return [
            "Right now: Keep one boundary that protects your evenings (e.g., no email after a set time).",
            "This week: Pick one efficiency win (template, batching, or a 10-minute plan routine).",
            "Keep it steady: Check in early if workload begins creeping up.",
        ]
    if level == "Amber":
        return [
            "Right now: Pause one non-urgent task for 48 hours (a deliberate ‘stop doing’).",
            "This week: Set one boundary + one shortcut (cut-off time + email batching / templates).",
            "If it continues: Talk to a trusted colleague/mentor or union rep about workload supports.",
        ]
    return [
        "Right now: High overload risk — reduce inputs for 24–48 hours and prioritise rest.",
        "This week: Arrange support (mentor/management) and identify what can be dropped or shared.",
        "Access confidential support via the Employee Assistance Service (EAS).",
    ]


# ----------------------------
# NAV STATE (sidebar buttons)
# ----------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "nickname" not in st.session_state:
    st.session_state.nickname = ""


def set_page(page_name: str):
    st.session_state.page = page_name


# ----------------------------
# SIDEBAR
# ----------------------------
st.sidebar.title("Teach Hub")
show_logo(where="sidebar")

if st.sidebar.button("🏠 Home", use_container_width=True):
    set_page("Home")
if st.sidebar.button("🏁 Teacher Challenges", use_container_width=True):
    set_page("Challenges")
if st.sidebar.button("💬 Community of Practice", use_container_width=True):
    set_page("Community")
if st.sidebar.button("🔗 Supports & Links", use_container_width=True):
    set_page("Supports")
if st.sidebar.button("🧠 Wellbeing Check-in", use_container_width=True):
    set_page("Wellbeing")
if st.sidebar.button("💰 Pay, Leave & Tax", use_container_width=True):
    set_page("Pay")
if st.sidebar.button("🎓 NQT Hub", use_container_width=True):
    set_page("NQT")
if st.sidebar.button("📚 Classroom Practice", use_container_width=True):
    set_page("Practice")
if st.sidebar.button("ℹ️ About", use_container_width=True):
    set_page("About")

st.sidebar.markdown("---")
st.sidebar.subheader("Nickname")

st.session_state.nickname = clean_nickname(
    st.sidebar.text_input(
        "Nickname (required for posting & logging)",
        value=st.session_state.nickname,
        placeholder="e.g., NQT2026, GaeilgeGuy, MsH",
        help="Nicknames keep the community friendly and privacy-safe.",
    )
)

if st.session_state.nickname.strip() == "":
    st.sidebar.info("Browse freely. Add a nickname to post, reply, or log challenges.")
else:
    st.sidebar.success(f"Using: {st.session_state.nickname}")

with st.sidebar.expander("Demo controls"):
    if st.button("Clear my nickname"):
        st.session_state.nickname = ""
        st.rerun()

# ----------------------------
# PAGES
# ----------------------------
def page_home():
    show_logo(where="main", width=170)

    st.title("Teach Hub")
    st.subheader("Connect. Support. Thrive.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### ✅ Quick Check-in")
        st.write("Do a fast wellbeing check and get practical advice.")
        if st.button("Go to Wellbeing Check-in"):
            st.session_state.page = "Wellbeing"
            st.rerun()

    with col2:
        st.markdown("### 🏁 Daily Challenges")
        st.write("Small actions that build momentum and reduce overwhelm.")
        if st.button("Go to Teacher Challenges"):
            st.session_state.page = "Challenges"
            st.rerun()

    with col3:
        st.markdown("### 🎓 NQT Starter Pack")
        st.write("Droichead, contracts, roles, school structures, and practical guidance.")
        if st.button("Go to NQT Hub"):
            st.session_state.page = "NQT"
            st.rerun()

    st.markdown("---")

    cA, cB = st.columns([2, 1])
    with cA:
        st.markdown("### What’s inside Teach Hub")
        st.write(
            "A practical support space for teachers: wellbeing check-ins, daily challenges, trusted links, pay/leave clarity, "
            "NQT guidance (including Droichead), classroom strategies, and a supportive community board."
        )
    with cB:
        st.markdown("### Today’s tip")
        tips = [
            "Batch emails: check at set times instead of constantly.",
            "Use templates for parent communication — saves serious time.",
            "Ask for the behaviour referral pathway early (don’t guess).",
            "One boundary beats ten good intentions — pick ONE and keep it.",
            "Small wins build momentum — finish one tiny task first.",
        ]
        st.info(tips[datetime.now().day % len(tips)])


def page_challenges():
    st.title("🏁 Teacher Challenges")
    st.write("Small, practical actions to help you stay in the **sweet spot** (focused, calm, effective).")

    require_nickname_or_stop()
    author = st.session_state.nickname.strip()

    # Date selector (today by default)
    colA, colB, colC = st.columns([1, 1, 2])
    with colA:
        selected = st.date_input("Log date", value=date.today())
    log_date = selected.strftime("%Y-%m-%d")

    # Dashboard stats
    with colB:
        streak = compute_streak(author)
        st.metric("Streak", f"{streak} day(s)")
    with colC:
        week_start = date.today() - timedelta(days=date.today().weekday())  # Monday
        week_end = week_start + timedelta(days=6)
        week_done = completed_count_in_range(author, week_start, week_end)
        today_done = daily_completion_total(author, today_str())
        st.write(f"**This week:** {week_done} completions (Mon–Sun)")
        st.write(f"**Today:** {today_done} completions")

    st.markdown("---")

    # Guide card (compact)
    with st.container(border=True):
        st.markdown("### Quick guide: stress → performance")
        st.write(
            "Stress becomes harmful when it shifts into **threat mode** (avoidance, panic, mistakes). "
            "These challenges are designed to push you back into **challenge mode** (approach, clarity, control)."
        )

    # Challenges checklist
    challenges = fetch_challenges()
    existing = fetch_user_logs(author, log_date)

    st.markdown("### Today’s challenges")
    st.caption("Tick what you complete. Your progress saves automatically.")

    # Group by category
    by_cat: Dict[str, List[Tuple[str, str, str, str, int]]] = {}
    for code, title, cat, instruction, seconds in challenges:
        by_cat.setdefault(cat, []).append((code, title, cat, instruction, seconds))

    for cat, items in by_cat.items():
        with st.expander(cat, expanded=True):
            for code, title, _cat, instruction, seconds in items:
                default_checked = bool(existing.get(code, 0))
                k = f"chk_{log_date}_{code}"

                checked = st.checkbox(
                    f"**{title}**  ·  ~{max(10, seconds)//60 if seconds >= 60 else seconds}s",
                    value=default_checked,
                    key=k
                )
                st.write(instruction)

                # Save immediately (no big submit button needed)
                set_challenge_completion(author, log_date, code, 1 if checked else 0)

                st.markdown("---")

    # Reflection (optional)
    st.markdown("### Optional reflection (1 minute)")
    current_ref = fetch_reflection(author, log_date)

    win = st.text_input("One small win today", value=current_ref["win"], key=f"ref_win_{log_date}")
    stress_shift = st.text_input("Stress shift: what helped most?", value=current_ref["stress_shift"], key=f"ref_shift_{log_date}")
    note = st.text_area("Any note (optional)", value=current_ref["note"], height=90, key=f"ref_note_{log_date}")

    if st.button("Save reflection", key=f"save_ref_{log_date}"):
        save_reflection(author, log_date, win, stress_shift, note)
        st.success("Saved ✅")


def page_supports():
    st.title("🔗 Supports & Links")
    st.write("Trusted supports and professional resources in one place.")

    st.markdown("## Key supports")
    for item in SUPPORT_LINKS:
        with st.container(border=True):
            st.markdown(f"**{item['name']}**")
            st.write(item["desc"])
            st.link_button("Open link", item["url"])

    st.markdown("---")
    st.markdown("## Community guidance")
    st.write(
        "Teach Hub is designed for supportive, practical discussion. "
        "Avoid sharing personal/sensitive details about students, colleagues, or schools."
    )


def page_wellbeing():
    st.title("🧠 Wellbeing Check-in")
    st.write(
        "Slide each scale. **1 = doing well, 10 = struggling**. "
        "You’ll get practical suggestions based on your inputs."
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        workload = st.slider(
            "Workload pressure (1 = manageable, 10 = overwhelming)", 1, 10, 3, key="wb_workload"
        )
        exhaustion = st.slider(
            "Emotional exhaustion (1 = energised, 10 = drained)", 1, 10, 3, key="wb_exhaustion"
        )
        sleep_problem = st.slider(
            "Sleep / recovery difficulty (1 = sleeping well, 10 = poor sleep)", 1, 10, 3, key="wb_sleep_problem"
        )
        support_problem = st.slider(
            "Lack of support at school (1 = well supported, 10 = not supported)", 1, 10, 3, key="wb_support_problem"
        )
        boundary_problem = st.slider(
            "Work-life boundaries difficulty (1 = strong boundaries, 10 = no boundaries)", 1, 10, 3, key="wb_boundary_problem"
        )

        if st.button("Get my summary", key="wb_submit"):
            level, score = wellbeing_assessment(
                workload, exhaustion, sleep_problem, support_problem, boundary_problem
            )
            st.session_state.wellbeing_result = (level, score)

    with col2:
        st.markdown("### Your output")
        if "wellbeing_result" not in st.session_state:
            st.info("Adjust the sliders and click **Get my summary**.")
        else:
            level, score = st.session_state.wellbeing_result

            if level == "Green":
                st.success(f"Status: **GREEN** (score {score})")
            elif level == "Amber":
                st.warning(f"Status: **AMBER** (score {score})")
            else:
                st.error(f"Status: **RED** (score {score})")
                st.markdown("### Immediate support")
                st.write("If you feel overwhelmed, confidential support is available:")
                st.link_button("Employee Assistance Service (EAS)", EAS_URL)

            st.markdown("#### Suggested actions")
            for line in advice_for_level(level):
                st.write("• " + line)

            st.markdown("---")
            st.caption(
                "Note: This tool provides general wellbeing guidance and is not medical advice. "
                "If you feel at risk or overwhelmed, seek professional support."
            )


def page_pay():
    st.title("💰 Pay, Leave & Tax")
    st.write("Clear explanations of common payroll/entitlement questions.")

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("📄 Payslip breakdown: what things mean"):
            for p in PAYSLIP_POINTS:
                st.write("• " + p)

        with st.expander("🚲 Bike to Work scheme: what it is"):
            for p in BIKE_TO_WORK_POINTS:
                st.write("• " + p)

        with st.expander("🧾 Flat-rate & medical expenses: what can you claim?"):
            for p in FLAT_RATE_MEDICAL_POINTS:
                st.write("• " + p)

        with st.expander("💶 Tax: the basics (PAYE, USC, PRSI)"):
            for p in TAX_POINTS:
                st.write("• " + p)

    with col2:
        with st.expander("🤒 Sick leave & sick pay: what to do"):
            for p in SICK_LEAVE_POINTS:
                st.write("• " + p)

        with st.expander("🤰 Maternity: steps & timing"):
            for p in MATERNITY_POINTS:
                st.write("• " + p)

        with st.expander("🌞 Summer / holiday social welfare if you don’t have a full contract"):
            for p in SUMMER_WELFARE_POINTS:
                st.write("• " + p)

        with st.expander("🏫 School structures: Croke Park hours & S&S duty"):
            for p in SCHOOL_STRUCTURES_POINTS:
                st.write("• " + p)

    st.markdown("---")
    st.info("Reminder: For contract-specific advice, your union (ASTI/TUI) is the best first stop.")


def page_nqt():
    st.title("🎓 NQT Hub")
    st.write("A starter pack for newly qualified teachers: Droichead, contracts, school life, roles, and supports.")

    # Always visible Droichead link at top (can’t be missed)
    st.link_button("Teaching Council — Droichead guidance", DROICHEAD_URL)

    st.markdown("---")

    for title, bullets in NQT_SECTIONS.items():
        with st.expander(title):
            for b in bullets:
                st.write("• " + b)
            if "Droichead" in title:
                st.link_button("Open Droichead page", DROICHEAD_URL)

    st.markdown("---")
    st.markdown("### Quick links")
    cols = st.columns(4)
    with cols[0]:
        st.link_button("Teaching Council", "https://www.teachingcouncil.ie/")
    with cols[1]:
        st.link_button("ASTI", "https://www.asti.ie/")
    with cols[2]:
        st.link_button("TUI", "https://www.tui.ie/")
    with cols[3]:
        st.link_button("Oide", "https://oide.ie/")

    st.markdown("---")
    st.markdown("### Ask an NQT question")
    st.write("Post into the Community under **NQT questions** for peer support.")
    if st.button("Go to Community (NQT questions)"):
        st.session_state._pref_cat = "NQT questions"
        st.session_state.page = "Community"
        st.rerun()


def page_practice():
    st.title("📚 Classroom Practice")
    st.write("Practical strategies for classroom management and supporting project work.")

    col1, col2 = st.columns(2)

    with col1:
        with st.expander("🧠 Classroom management strategies"):
            for p in CLASSROOM_MGMT_POINTS:
                st.write("• " + p)

        with st.expander("🧪 Supporting project work in the classroom"):
            for p in PROJECT_WORK_POINTS:
                st.write("• " + p)

    with col2:
        with st.expander("🧩 Quick behaviour toolkit (simple steps)"):
            st.write("• Be at the door: greet, seat, starter task on board.")
            st.write("• Narrate positives: highlight the behaviour you want repeated.")
            st.write("• Calm correction: short, private, specific.")
            st.write("• Reset routine: give a clear “next step” after correction.")
            st.write("• Follow policy: use the school’s pathway consistently.")

        with st.expander("🗂 Project support toolkit (weekly structure)"):
            st.write("• Week plan: one target, one deliverable, one reflection.")
            st.write("• Progress log: students write ‘What I did’ + ‘Next step’.")
            st.write("• Evidence: photos, tables, drafts in one folder.")
            st.write("• Mini-checkpoints: method approved → data verified → analysis checked.")
            st.write("• Final polish: references, captions, clear charts, limitations.")


def page_community():
    st.title("💬 Community of Practice")
    st.write("Ask questions, share strategies, and support one another.")

    default_cat = st.session_state.get("_pref_cat", "All")

    colA, colB = st.columns([1, 1])

    # Create post
    with colA:
        st.markdown("### Create a post")
        st.caption("You need a nickname (sidebar) to post or reply.")

        category = st.selectbox("Category", COMMUNITY_CATEGORIES, index=0, key="cp_category")
        title = st.text_input("Title", key="cp_title")
        body = st.text_area("What’s your question or tip?", height=140, key="cp_body")

        if st.button("Post", key="cp_post_btn"):
            require_nickname_or_stop()
            if not title.strip() or not body.strip():
                st.warning("Please add a title and some text.")
            else:
                add_post(st.session_state.nickname.strip(), category, title, body)
                st.success("Posted!")
                st.session_state.cp_title = ""
                st.session_state.cp_body = ""
                st.rerun()

    # Browse posts
    with colB:
        st.markdown("### Browse posts")
        search_text = st.text_input("Search", "", key="cp_search")

        cat_options = ["All"] + COMMUNITY_CATEGORIES
        cat_index = cat_options.index(default_cat) if default_cat in cat_options else 0
        category_filter = st.selectbox("Filter by category", cat_options, index=cat_index, key="cp_filter")

        posts = fetch_posts(search_text=search_text, category_filter=category_filter)

        if not posts:
            st.info("No posts yet — start the conversation!")
        else:
            for post_id, created_at, author, category, title, body in posts:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.caption(f"{created_at} • {category} • by {author}")
                    st.write(body)

                    replies = fetch_replies(post_id)
                    if replies:
                        st.markdown("**Replies:**")
                        for r_created, r_author, r_body in replies:
                            st.write(f"— *{r_author}* ({r_created}): {r_body}")

                    with st.expander("Reply"):
                        reply_key = f"reply_{post_id}"
                        reply_text = st.text_area(
                            "Write a reply",
                            key=reply_key,
                            height=80,
                            placeholder="Share a strategy, ask a clarifying question, or offer support…",
                        )
                        if st.button("Submit reply", key=f"btn_{post_id}"):
                            require_nickname_or_stop()
                            if reply_text.strip():
                                add_reply(post_id, st.session_state.nickname.strip(), reply_text)
                                st.success("Reply added.")
                                st.session_state[reply_key] = ""
                                st.rerun()
                            else:
                                st.warning("Reply cannot be empty.")

    if "_pref_cat" in st.session_state:
        del st.session_state["_pref_cat"]


def page_about():
    st.title("ℹ️ About / Disclaimer")
    st.write(
        """
Teach Hub supports teachers through:
- a community of practice space,
- curated supports and links,
- a wellbeing check-in tool,
- daily teacher challenges,
- pay/leave/tax explanations,
- NQT guidance (including Droichead), and
- classroom practice strategies.

**Disclaimer:** Teach Hub provides general guidance and signposting only.
It does not provide legal, medical, payroll, or professional advice.
For contract-specific issues, consult your union and official sources.
If you are in crisis or at risk, seek urgent support through appropriate services.
        """
    )

# ----------------------------
# RENDER
# ----------------------------
page = st.session_state.page

if page == "Home":
    page_home()
elif page == "Challenges":
    page_challenges()
elif page == "Community":
    page_community()
elif page == "Supports":
    page_supports()
elif page == "Wellbeing":
    page_wellbeing()
elif page == "Pay":
    page_pay()
elif page == "NQT":
    page_nqt()
elif page == "Practice":
    page_practice()
else:
    page_about()
