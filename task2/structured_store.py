import os, json
import pandas as pd
from dateutil import parser

def parse_date_safe(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    try:
        return parser.parse(s, dayfirst=True, fuzzy=True)
    except Exception:
        return None

class StructuredStore:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.emp = pd.DataFrame()
        self.leave = pd.DataFrame()
        self.att_by_emp = {}  # dict: EMP1001 -> list[events]

    def load(self):
        emp_path = os.path.join(self.data_dir, "employee_master.csv")
        leave_path = os.path.join(self.data_dir, "leave_intelligence.xlsx")
        att_path = os.path.join(self.data_dir, "attendance_logs_detailed.json")

        self.emp = pd.read_csv(emp_path)
        self.leave = pd.read_excel(leave_path)
        with open(att_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # IMPORTANT: your attendance JSON is dict keyed by EMP ID
        if not isinstance(raw, dict):
            raise RuntimeError("attendance_logs_detailed.json must be a dict keyed by emp_id (EMP1001 -> [...])")
        self.att_by_emp = raw

        self._normalize_dates()

    def _normalize_dates(self):
        # Normalize dates in employee + leave
        for df in [self.emp, self.leave]:
            for c in df.columns:
                if any(t in c.lower() for t in ["date", "dob", "doj", "join", "from", "to", "time", "timestamp"]):
                    df[c] = df[c].apply(parse_date_safe)

        # Normalize dates inside attendance dict events (if event has date/timestamp fields)
        for emp_id, events in self.att_by_emp.items():
            if isinstance(events, list):
                for ev in events:
                    if isinstance(ev, dict):
                        for k in list(ev.keys()):
                            if any(t in k.lower() for t in ["date", "time", "timestamp"]):
                                ev[k] = parse_date_safe(ev[k])

    def _pick_col(self, df: pd.DataFrame, options):
        cols = {c.lower(): c for c in df.columns}
        for o in options:
            if o.lower() in cols:
                return cols[o.lower()]
        # heuristic
        for c in df.columns:
            cl = c.lower()
            if "emp" in cl and ("id" in cl or "code" in cl or "no" in cl):
                return c
        return None

    def get_employee(self, emp_id: str):
        id_col = self._pick_col(self.emp, ["emp_id", "employee_id", "employeeid", "empcode", "employee_code"])
        if not id_col:
            return None, "Employee master missing emp id column"
        sub = self.emp[self.emp[id_col].astype(str).str.upper().str.strip() == str(emp_id).upper().strip()]
        if sub.empty:
            return None, f"Employee not found for {emp_id}"
        if len(sub) > 1:
            return None, f"Ambiguous employee id {emp_id} (multiple matches)"
        return sub.iloc[0].to_dict(), None

    def get_leave_rows(self, emp_id: str):
        id_col = self._pick_col(self.leave, ["emp_id", "employee_id", "employeeid", "empcode", "employee_code"])
        if not id_col:
            return [], "Leave sheet missing emp id column"
        sub = self.leave[self.leave[id_col].astype(str).str.upper().str.strip() == str(emp_id).upper().strip()]
        return sub.to_dict(orient="records"), None

    def get_attendance(self, emp_id: str):
        emp_id = str(emp_id).upper().strip()
        events = self.att_by_emp.get(emp_id)
        if not events:
            return None, f"No attendance found for {emp_id}"
        return events, None
