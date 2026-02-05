def detect_intent(question: str):
    q = question.lower()

    if "leave" in q and ("how many" in q or "left" in q or "balance" in q):
        return "LEAVE_BALANCE"

    if "can i take leave" in q or "allowed to take leave" in q:
        return "LEAVE_POLICY"

    if "eligible" in q:
        return "ELIGIBILITY"

    if "attendance" in q or "absent" in q:
        return "ATTENDANCE_SUMMARY"

    if "policy" in q or "rule" in q:
        return "POLICY_ONLY"

    return "GENERAL"
