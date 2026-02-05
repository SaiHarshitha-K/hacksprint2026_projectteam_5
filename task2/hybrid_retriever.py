import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from structured_store import StructuredStore
from intent_router import detect_intent
from rule_dispatcher import apply_rules

DATA_DIR = "data"
FAISS_PATH = os.path.join(DATA_DIR, "helix_unstructured.faiss")
META_PATH = os.path.join(DATA_DIR, "helix_unstructured.pkl")


def _safe_sample(x, n=5):
    """Return a safe sample from list/dict/other."""
    if x is None:
        return []
    if isinstance(x, list):
        return x[:n]
    if isinstance(x, dict):
        # sample first n items as dict (small) OR values list
        items = list(x.items())[:n]
        return [{k: v} for k, v in items]
    return [str(x)[:300]]


def _to_list_of_events(att):
    """
    Normalize attendance to a list of events.
    Handles:
      - list[dict]
      - dict -> list(dict.values()) OR list(items)
    """
    if att is None:
        return []
    if isinstance(att, list):
        return att
    if isinstance(att, dict):
        # Most common: dict of events -> values are events
        vals = list(att.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return vals
        # Otherwise: dict keyed by something -> keep as list of {k:v}
        return [{k: v} for k, v in list(att.items())]
    # unknown type
    return []


class UnstructuredDB:
    """
    Vector DB wrapper for PDF+TXT FAISS index.
    Expects:
      data/helix_unstructured.faiss
      data/helix_unstructured.pkl  with {"chunks": [...], "meta":[{"source":...}, ...]}
    """

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        if not os.path.exists(FAISS_PATH) or not os.path.exists(META_PATH):
            raise FileNotFoundError(
                "Vector DB files missing. Run: python index_unstructured.py\n"
                f"Expected:\n - {FAISS_PATH}\n - {META_PATH}"
            )

        self.embedder = SentenceTransformer(model_name)
        self.index = faiss.read_index(FAISS_PATH)

        with open(META_PATH, "rb") as f:
            obj = pickle.load(f)

        self.chunks = obj.get("chunks", [])
        self.meta = obj.get("meta", [])

        if not self.chunks or not self.meta or len(self.chunks) != len(self.meta):
            raise RuntimeError("Invalid vector metadata: chunks/meta missing or lengths mismatch.")

    def search(self, query: str, k=6, score_threshold=0.25):
        q = self.embedder.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype(np.float32)

        scores, idx = self.index.search(q, k)

        results = []
        for s, i in zip(scores[0], idx[0]):
            if i == -1:
                continue
            s = float(s)
            if s < score_threshold:
                continue

            src = self.meta[i].get("source", "unknown")
            results.append({
                "score": s,
                "text": self.chunks[i],
                "source": src
            })
        return results


# def build_context(query: str, emp_id: str | None, store: StructuredStore, udb: UnstructuredDB):
#     """
#     Hybrid retrieval:
#       - Unstructured: FAISS semantic search over policy PDF + Readme TXT
#       - Structured: CSV/Excel/Data dict lookups for employee/leave/attendance
#       - Business rules: deterministic HR calculations
#     """
#     query = (query or "").strip()
#     emp_id_norm = emp_id.strip().upper() if emp_id else None

#     context_blocks = []
#     citations = []

#     # ---------------------------
#     # 1) Unstructured retrieval (POLICY / TEXT)
#     # ---------------------------
#     if query:
#         hits = udb.search(query, k=6, score_threshold=0.25)
#         for j, h in enumerate(hits[:3], start=1):
#             context_blocks.append({
#                 "title": f"Policy/Text hit #{j} (score={h['score']:.2f})",
#                 "text": h["text"],
#                 "source": h["source"],
#             })

#         if hits:
#             citations.append({
#                 "source": "VectorDB(FAISS)",
#                 "note": f"Sources hit: {sorted(set([h['source'] for h in hits]))}"
#             })

#     # ---------------------------
#     # 2) Structured retrieval (EMPLOYEE DATA)
#     # ---------------------------
#     emp = None
#     leave_rows = []
#     attendance_events = []

#     if emp_id_norm:
#         emp, err = store.get_employee(emp_id_norm)
#         if err:
#             return [], [], f"INSUFFICIENT_DATA: {err}"

#         # Employee record
#         context_blocks.append({
#             "title": "Employee record (structured)",
#             "text": str(emp),
#             "source": "employee_master.csv"
#         })
#         citations.append({
#             "source": "employee_master.csv",
#             "note": f"emp_id={emp_id_norm}"
#         })

#         # Leave rows
#         leave_rows, lerr = store.get_leave_rows(emp_id_norm)
#         if not lerr and leave_rows:
#             context_blocks.append({
#                 "title": "Leave rows (structured)",
#                 "text": str(leave_rows[:10]),
#                 "source": "leave_intelligence.xlsx"
#             })
#             citations.append({
#                 "source": "leave_intelligence.xlsx",
#                 "note": f"rows={len(leave_rows)}"
#             })

#         # Attendance
#         att, aerr = store.get_attendance(emp_id_norm)
#         if not aerr and att:
#             attendance_events = _to_list_of_events(att)
#             context_blocks.append({
#                 "title": "Attendance summary (semi-structured)",
#                 "text": f"count={len(attendance_events)} sample={_safe_sample(attendance_events, 5)}",
#                 "source": "attendance_logs_detailed.json"
#             })
#             citations.append({
#                 "source": "attendance_logs_detailed.json",
#                 "note": f"events={len(attendance_events)}"
#             })

#     # ---------------------------
#     # 3) 🔑 BUSINESS RULES (THIS IS WHAT YOU ASKED)
#     # ---------------------------
#     intent = detect_intent(query)

#     computed_blocks = apply_rules(
#         intent=intent,
#         emp=emp,
#         leave_rows=leave_rows,
#         attendance=attendance_events
#     )

#     for block in computed_blocks:
#         context_blocks.append(block)
#         citations.append({
#             "source": block["source"],
#             "note": "computed business rule"
#         })

#     # ---------------------------
#     # 4) Guardrail
#     # ---------------------------
#     if not context_blocks:
#         return [], [], "INSUFFICIENT_DATA: No relevant policy text found and no employee id provided."

#     return context_blocks, citations, None

def build_context(query, emp_id, store, udb):
    context_blocks = []
    citations = []

    # 1️⃣ Intent
    intent = detect_intent(query)

    # 2️⃣ Structured data
    emp = store.get_employee(emp_id) if emp_id else None
    leave_rows = store.get_leave_rows(emp_id)[0] if emp_id else []
    attendance = store.get_attendance(emp_id)[0] if emp_id else []

    # 3️⃣ Unstructured data (PDF/TXT)
    policy_hits = udb.search(query)

    # 4️⃣ Business rules (if needed)
    computed_blocks = apply_rules(
        intent=intent,
        emp=emp,
        leave_rows=leave_rows,
        attendance=attendance
    )

    # 5️⃣ Assemble context
    if emp:
        context_blocks.append({
            "title": "Employee data",
            "text": str(emp),
            "source": "employee_master.csv"
        })

    for h in policy_hits[:3]:
        context_blocks.append({
            "title": "Policy excerpt",
            "text": h["text"],
            "source": h["source"]
        })

    context_blocks.extend(computed_blocks)

    if not context_blocks:
        return [], [], "INSUFFICIENT_DATA"

    return context_blocks, citations, None
