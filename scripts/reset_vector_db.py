"""
Reset Vector Database — Xóa và tái tạo Chroma DB từ chunks hiện có
Chạy: python scripts/reset_vector_db.py
"""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def reset_chroma_db(confirm: bool = False):
    from src.utils.config import CHROMA_DIR, CHUNKS_DIR
    
    print(f"\n⚠️  Sắp xóa toàn bộ Chroma DB tại: {CHROMA_DIR}")
    print(f"   Sẽ tái tạo từ chunks tại: {CHUNKS_DIR}")
    
    if not confirm:
        answer = input("\nBạn có chắc chắn? [y/N]: ").strip().lower()
        if answer != "y":
            print("❌ Hủy. Không có gì bị xóa.")
            return
    
    # Xóa Chroma DB
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
        CHROMA_DIR.mkdir(parents=True)
        print("✅ Đã xóa Chroma DB cũ")
    
    # Tái tạo từ chunks
    print("\n⏳ Đang tái tạo Vector DB từ chunks...")
    from scripts.build_knowledge_base import run_pipeline
    run_pipeline(chunks_only=True)
    print("✅ Hoàn thành!")

if __name__ == "__main__":
    reset_chroma_db()
