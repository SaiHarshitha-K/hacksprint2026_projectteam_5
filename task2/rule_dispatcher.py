from business_rules import (
    calculate_prorated_leave,
    calculate_leave_balance
)

def apply_rules(intent, emp=None, leave_rows=None, attendance=None):
    computed = []

    leave_rows = leave_rows or []
    attendance = attendance or []

    # -------------------------
    # Leave balance
    # -------------------------
    if intent == "LEAVE_BALANCE" and emp:
        taken = len(leave_rows)
        remaining = max(15 - taken, 0)

        computed.append({
            "title": "Leave balance (computed)",
            "text": f"Annual quota: 15 days. Leaves taken: {taken}. Remaining balance: {remaining}.",
            "source": "business_rules.py"
        })

    # -------------------------
    # Leave entitlement (prorated)
    # -------------------------
    if intent == "LEAVE_ENTITLEMENT" and emp:
        doj = emp.get("date_of_joining") or emp.get("doj") or emp.get("joining_date")

        if doj:
            from business_rules import calculate_prorated_leave
            leave, meta = calculate_prorated_leave(doj)

            computed.append({
                "title": "Leave entitlement (computed)",
                "text": (
                    f"Joining date: {doj}. "
                    f"Months worked in 2026: {meta['months_worked']}. "
                    f"Annual quota: {meta['annual_quota']} days. "
                    f"Entitled leave: {leave} days."
                ),
                "source": "business_rules.py"
            })

    # -------------------------
    # Attendance summary
    # -------------------------
    if intent == "ATTENDANCE_SUMMARY" and attendance:
        computed.append({
            "title": "Attendance summary (computed)",
            "text": f"Total attendance records found: {len(attendance)}.",
            "source": "attendance_logs_detailed.json"
        })

    return computed
