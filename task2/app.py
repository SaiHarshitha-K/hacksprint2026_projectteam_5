import streamlit as st
from structured_store import StructuredStore
from hybrid_retriever import UnstructuredDB, build_context
from gemini_answer import answer_with_gemini

st.set_page_config(page_title="Helix HR Bot", layout="wide")

@st.cache_resource
def load_system():
    store = StructuredStore("data")
    store.load()
    udb = UnstructuredDB()
    return store, udb

store, udb = load_system()

st.title("🏢 Helix HR Intelligence Bot (Hybrid RAG)")
st.caption("PDF+TXT → Vector DB (FAISS). CSV/Excel/JSON → deterministic lookup. Gemini generates only from context.")

with st.sidebar:
    emp_id = st.text_input("Employee ID (optional)", value="").strip() or None

query = st.text_area("Ask a question", placeholder="E.g., What is the policy for missing check-out? Or show attendance summary for EMP1001")
if st.button("Ask") and query.strip():
    context_blocks, citations, err = build_context(query.strip(), emp_id, store, udb)

    if err:
        st.error(err)
    else:
        ans = answer_with_gemini(query.strip(), context_blocks)

        st.subheader("Answer")
        st.write(ans)

        st.subheader("Citations used")
        for c in citations:
            st.write(f"- **{c['source']}**: {c['note']}")

        st.subheader("Debug: Context blocks")
        with st.expander("Show retrieved context"):
            for b in context_blocks:
                st.markdown(f"**{b['title']}** — `{b['source']}`")
                st.write(b["text"][:800] + ("..." if len(b["text"]) > 800 else ""))
