"""
Phase 1 — Kiểm thử chẩn đoán từng component
Chạy: python tests/test_pipeline_diagnostic.py
"""
import sys
import io
import logging
from pathlib import Path

# Fix encoding Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.WARNING)  # Tắt bớt noise logs

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = {}

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(name, status, detail=""):
    icon = PASS if status else FAIL
    print(f"  {icon}  {name}")
    if detail:
        print(f"       → {detail}")
    results[name] = status

# ============================================================
# TEST 1: Import thư viện
# ============================================================
section("TEST 1: Import dependencies")

try:
    import yaml; check("yaml", True)
except: check("yaml", False)

try:
    import chromadb; check("chromadb", True, f"version: {chromadb.__version__}")
except: check("chromadb", False)

try:
    from langchain_huggingface import HuggingFaceEmbeddings; check("langchain_huggingface", True)
except: check("langchain_huggingface", False)

try:
    from langchain_ollama import OllamaLLM; check("langchain_ollama", True)
except: check("langchain_ollama", False)

try:
    from langchain_chroma import Chroma; check("langchain_chroma", True)
except: check("langchain_chroma", False)

try:
    import streamlit; check("streamlit", True, f"version: {streamlit.__version__}")
except: check("streamlit", False)

# ============================================================
# TEST 2: Import project modules
# ============================================================
section("TEST 2: Import project modules")

try:
    from src.embeddings.model import EmbeddingModelManager
    check("EmbeddingModelManager", True)
except Exception as e:
    check("EmbeddingModelManager", False, str(e))

try:
    from src.embeddings.vector_db import VectorDatabaseManager
    check("VectorDatabaseManager", True)
except Exception as e:
    check("VectorDatabaseManager", False, str(e))

try:
    from src.agent.state import AgentState
    check("AgentState", True)
except Exception as e:
    check("AgentState", False, str(e))

try:
    from src.agent.orchestrator import StudentRegulationAgent
    check("StudentRegulationAgent", True)
except Exception as e:
    check("StudentRegulationAgent", False, str(e))

# ============================================================
# TEST 3: Kiểm tra files & dữ liệu
# ============================================================
section("TEST 3: Files & Data")

config_ok = Path("./config.yaml").exists()
check("config.yaml tồn tại", config_ok)

chroma_db = Path("./data/chroma/chroma.sqlite3")
check("Chroma DB file tồn tại", chroma_db.exists(),
      f"size: {chroma_db.stat().st_size / 1024 / 1024:.1f} MB" if chroma_db.exists() else "missing")

chunks_dir = Path("./data/chunks")
chunk_files = list(chunks_dir.glob("*.json")) if chunks_dir.exists() else []
check("Chunk files tồn tại", len(chunk_files) > 0, f"{len(chunk_files)} files found")

pdf_dir = Path("./knowledge_base/raw")
pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
check("PDF nguồn tồn tại", len(pdf_files) > 0, f"{len(pdf_files)} PDFs: " + ", ".join(f.name for f in pdf_files[:3]))

# ============================================================
# TEST 4: Kết nối Ollama
# ============================================================
section("TEST 4: Ollama Connection")
try:
    import requests
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in models]
        has_mistral = any("mistral" in m.lower() for m in model_names)
        check("Ollama server running", True, f"models: {model_names}")
        check("Mistral model available", has_mistral,
              "mistral found" if has_mistral else f"Chỉ có: {model_names} — chạy: ollama pull mistral")
    else:
        check("Ollama server running", False, f"HTTP {resp.status_code}")
except Exception as e:
    check("Ollama server running", False, f"{e} — Chạy: ollama serve")

# ============================================================
# TEST 5: Khởi tạo Embedding Model
# ============================================================
section("TEST 5: Embedding Model (bge-m3)")
print("  ⏳ Đang load embedding model (có thể mất 30-60 giây lần đầu)...")

try:
    from src.embeddings.model import EmbeddingModelManager
    em = EmbeddingModelManager("./config.yaml")
    embeddings = em.get_model()
    # Test encode thử 1 câu
    test_vec = embeddings.embed_query("học phí sinh viên ĐHBK Hà Nội")
    check("Embedding Model load", True, f"vector dim: {len(test_vec)}")
except Exception as e:
    check("Embedding Model load", False, str(e))
    embeddings = None

# ============================================================
# TEST 6: Kết nối Chroma DB & Kiểm tra dữ liệu
# ============================================================
section("TEST 6: Chroma DB & Retrieval")

if embeddings:
    try:
        from src.embeddings.vector_db import VectorDatabaseManager
        vdb = VectorDatabaseManager(embeddings=embeddings, config_path="./config.yaml")

        # Đếm documents
        info = vdb.get_collection_info()
        doc_count = info.get("count", 0)
        check("Chroma DB connect", True, f"collection: '{info.get('collection_name')}', docs: {doc_count}")
        check("Chroma DB có dữ liệu", doc_count > 0, f"{doc_count} vectors")

        # Test retrieval với các câu hỏi thực tế
        test_queries = [
            "Học phí sinh viên",
            "GPA cảnh báo học vụ",
            "Điều kiện nhận học bổng Trần Đại Nghĩa",
            "Chuẩn ngoại ngữ K68",
            "Học lại học phần",
        ]

        print(f"\n  📊 Kết quả Retrieval Test ({len(test_queries)} queries):")
        all_ok = True
        for query in test_queries:
            results_q = vdb.search_similar(query, k=3, score_threshold=0.0)
            ok = len(results_q) > 0
            if not ok:
                all_ok = False
            # In kết quả top-1
            if results_q:
                doc, score = results_q[0]
                source = doc.metadata.get("source_file", doc.metadata.get("source", "?"))
                chapter = doc.metadata.get("chapter_title", "")[:30]
                article = doc.metadata.get("article_title", "")[:40]
                print(f"    Query: '{query}'")
                print(f"    → score={score:.3f} | src={source} | {article}")
                print()
            else:
                print(f"    Query: '{query}' → ❌ No results!")

        check("Retrieval trả về kết quả", all_ok)

    except Exception as e:
        check("Chroma DB connect", False, str(e))
        import traceback; traceback.print_exc()
else:
    print(f"  ⚠️  Bỏ qua — Embedding model chưa load được")

# ============================================================
# TEST 7: Khởi tạo Agent (nếu Ollama sẵn sàng)
# ============================================================
section("TEST 7: Agent Initialization")
print("  ⏳ Đang khởi tạo StudentRegulationAgent...")

try:
    from src.agent import StudentRegulationAgent
    agent = StudentRegulationAgent(config_path="./config.yaml")
    check("Agent khởi tạo thành công", True)

    # Test 1 câu hỏi
    print("\n  ⏳ Test câu hỏi: 'Điểm thi dưới bao nhiêu thì bị điểm liệt?'")
    result = agent.answer_question("Điểm thi dưới bao nhiêu thì bị điểm liệt?")
    check("Agent trả lời được", result.get("success", False),
          f"confidence={result.get('confidence', 0):.0%}")
    if result.get("answer"):
        print(f"\n  💬 Câu trả lời:\n  {result['answer'][:300]}...")
    if result.get("state") and result["state"].sources:
        print(f"  📚 Nguồn: {result['state'].sources}")

except Exception as e:
    check("Agent khởi tạo thành công", False, str(e))
    import traceback; traceback.print_exc()

# ============================================================
# SUMMARY
# ============================================================
section("TỔNG KẾT")
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"  Kết quả: {passed}/{total} checks passed")
print()
for name, ok in results.items():
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}")

if passed == total:
    print(f"\n  🎉 Tất cả checks passed! Sẵn sàng bước tiếp theo.")
else:
    failed = [name for name, ok in results.items() if not ok]
    print(f"\n  ⚠️  Cần xử lý: {failed}")

print()
