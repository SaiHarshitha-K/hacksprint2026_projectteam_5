import os, pickle
import numpy as np
import fitz  # PyMuPDF
import faiss
from sentence_transformers import SentenceTransformer

DATA_DIR = "data"
PDF_PATH = os.path.join(DATA_DIR, "Helix_Pro_Policy_v2.pdf")
TXT_PATH = os.path.join(DATA_DIR, "Readme.txt")

FAISS_PATH = os.path.join(DATA_DIR, "helix_unstructured.faiss")
META_PATH  = os.path.join(DATA_DIR, "helix_unstructured.pkl")

def pdf_to_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    parts = []
    for i in range(len(doc)):
        parts.append(doc[i].get_text("text"))
    return "\n".join(parts)

def txt_to_text(txt_path: str) -> str:
    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200):
    text = text.replace("\r", "\n")
    chunks = []
    i = 0
    while i < len(text):
        ch = text[i:i+chunk_size].strip()
        if ch:
            chunks.append(ch)
        i += max(1, chunk_size - overlap)
    return chunks

def build_unstructured_index():
    docs = []

    if os.path.exists(PDF_PATH):
        docs.append(("Helix_Pro_Policy_v2.pdf", pdf_to_text(PDF_PATH)))
    else:
        raise FileNotFoundError(f"Missing PDF: {PDF_PATH}")

    if os.path.exists(TXT_PATH):
        docs.append(("Readme.txt", txt_to_text(TXT_PATH)))
    else:
        print("⚠️ Readme.txt not found — continuing without it.")

    # Build chunks + metadata
    all_chunks = []
    meta = []  # each chunk's source
    for source_name, text in docs:
        chunks = chunk_text(text)
        for ch in chunks:
            all_chunks.append(ch)
            meta.append({"source": source_name})

    print(f"Total chunks: {len(all_chunks)}")

    # Embed
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    emb = embedder.encode(all_chunks, convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)

    # FAISS index
    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(emb)

    # Save
    faiss.write_index(index, FAISS_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump({"chunks": all_chunks, "meta": meta}, f)

    print("✅ Saved:")
    print(" -", FAISS_PATH)
    print(" -", META_PATH)

if __name__ == "__main__":
    build_unstructured_index()
