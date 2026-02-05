from datetime import datetime

ANNUAL_LEAVE_QUOTA = 15

def calculate_prorated_leave(doj, year=2026):
    if doj is None:
        return None, "Joining date missing"

    year_start = datetime(year, 1, 1)
    year_end = datetime(year, 12, 31)

    if doj > year_end:
        return 0, {"months_worked": 0}

    effective = max(doj, year_start)

    months = (year_end.year - effective.year) * 12 + \
             (year_end.month - effective.month) + 1

    leave = round((ANNUAL_LEAVE_QUOTA / 12) * months, 2)

    return leave, {
        "months_worked": months,
        "annual_quota": ANNUAL_LEAVE_QUOTA
    }


def calculate_leave_balance(annual_quota, taken):
    return max(annual_quota - taken, 0)
