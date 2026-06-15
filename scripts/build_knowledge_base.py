"""
Ví dụ sử dụng module embedding
Tái cấu trúc từ data_preparation.py
"""
import json
import logging
import yaml
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Fix module path so 'src' can be imported when running from any directory
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.embeddings import (
    EmbeddingModelManager,
    PDFProcessor,
    TextChunker,
    VectorDatabaseManager
)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataPreparationPipelineRefactored:
    """
    Pipeline xử lý dữ liệu được tái cấu trúc
    Sử dụng các module từ src/embeddings
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Khởi tạo pipeline
        
        Args:
            kb_path: Đường dẫn thư mục chứa PDF
            output_path: Đường dẫn thư mục output (JSON, chunks, chroma)
            config_path: Đường dẫn tới config.yaml
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        data_paths = self.config.get("data_paths", {})
        self.kb_path = Path(data_paths.get("knowledge_base_raw", "./knowledge_base/raw"))
        self.output_path = Path(data_paths.get("output_base", "./data"))
        self.chunks_path = Path(data_paths.get("chunks_output", "./data/chunks"))
        self.chroma_path = Path(data_paths.get("chroma_db", "./data/chroma"))

        # Tạo thư mục output
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("=" * 80)
        logger.info("🚀 INITIALIZING DATA PREPARATION PIPELINE")
        logger.info("=" * 80)
        
        # 1️⃣ Khởi tạo model manager
        self.model_manager = EmbeddingModelManager(config_path)
        self.embeddings = self.model_manager.get_model()
        
        # 2️⃣ Khởi tạo vector database
        self.vector_db = VectorDatabaseManager(
            embeddings=self.embeddings,
            config_path=config_path
        )
        
        # Metadata mapping
        pdf_processing = self.config.get("pdf_processing", {})
        self.metadata_mapping = pdf_processing.get("metadata_mapping", {})
    
    def step_1_process_pdfs(self, config_path: str = "./config.yaml") -> int:
        """
        BƯỚC 1: Xử lý tất cả PDF files
        - Trích xuất text từ PDF
        - Làm sạch dữ liệu
        - Lưu thành JSON files
        
        Returns:
            Số lượng PDF đã xử lý
        """
        logger.info("\n" + "=" * 80)
        logger.info("📄 STEP 1: PROCESSING PDF FILES")
        logger.info("=" * 80)
        
        # Tìm tất cả file PDF
        pdf_files = [f for f in os.listdir(self.kb_path) 
                     if f.lower().endswith('.pdf')]
        
        logger.info(f"📊 Found {len(pdf_files)} PDF files\n")
        
        process_count = 0
        
        for pdf_name in pdf_files:
            pdf_path = self.kb_path / pdf_name
            
            logger.info(f"⏳ Processing: {pdf_name}")
            
            # Lấy metadata
            meta = self.metadata_mapping.get(pdf_name, {
                "doc_type": "Unknown",
                "effective_date": "Unknown",
                "applicable_students": "Unknown",
                "status": "Unknown"
            })
            
            meta['source_file'] = pdf_name
            meta['processed_date'] = datetime.now().isoformat()
            
            try:
                # Xử lý PDF
                content = PDFProcessor.process_pdf_file(str(pdf_path), config_path)
                
                if content:
                    # Tạo document object
                    document = {
                        "metadata": meta,
                        "content": content
                    }
                    
                    # Lưu thành JSON
                    output_file = self.output_path / f"{Path(pdf_name).stem}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(document, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"   ✅ Saved: {output_file.name}\n")
                    process_count += 1
                else:
                    logger.warning(f"   ⚠️  No content extracted\n")
                    
            except Exception as e:
                logger.error(f"   ❌ Error: {str(e)}\n")
        
        logger.info("=" * 80)
        logger.info(f"✨ PDF Processing Complete: {process_count} files processed")
        logger.info("=" * 80)
        
        return process_count
    
    def step_2_chunk_documents(self, config_path: str = "./config.yaml") -> int:
        """
        BƯỚC 2: Tách tất cả JSON documents thành chunks
        - Tách theo Markdown headers (Chương/Điều)
        - Tách theo kích thước chunk
        - Gắn metadata cho mỗi chunk
        
        Args:
            config_path: Đường dẫn tới config.yaml
        
        Returns:
            Số lượng chunks được tạo
        """
        logger.info("\n" + "=" * 80)
        logger.info("✂️  STEP 2: CHUNKING DOCUMENTS")
        logger.info("=" * 80)
        
        # Get chunk configuration from config
        with open(config_path, 'r', encoding='utf-8') as f:
            full_config = yaml.safe_load(f)
        chunk_size = full_config.get("chunking", {}).get("chunk_size", 1000)
        chunk_overlap = full_config.get("chunking", {}).get("chunk_overlap", 200)
        
        logger.info(f"📋 Chunking config:")
        logger.info(f"   - chunk_size: {chunk_size}")
        logger.info(f"   - chunk_overlap: {chunk_overlap}\n")
        
        # Tách tất cả documents
        all_chunks = TextChunker.chunk_all_documents(
            data_path=self.output_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            config_path=config_path
        )
    
        return len(all_chunks)
    
    def step_3_store_in_vectordb(self, chunks) -> None:
        """
        BƯỚC 3: Lưu chunks vào Vector Database (Chroma)
        - Embedding mỗi chunk
        - Lưu vào Chroma DB
        - Persist tới disk
        
        Args:
            chunks: List Document objects
        """
        logger.info("\n" + "=" * 80)
        logger.info("🗄️  STEP 3: STORING IN VECTOR DATABASE")
        logger.info("=" * 80)
        
        if not chunks:
            logger.warning("⚠️  No chunks to store")
            return
        
        try:
            # Thêm documents vào vector database
            num_added = self.vector_db.add_documents(chunks)
            
            # Hiển thị thông tin collection
            info = self.vector_db.get_collection_info()
            logger.info(f"\n📊 Collection Info:")
            logger.info(f"   - Name: {info.get('collection_name')}")
            logger.info(f"   - Documents: {info.get('count')}")
            logger.info(f"   - Location: {info.get('persist_directory')}")
            
            logger.info("\n" + "=" * 80)
            logger.info(f"✨ Vector Database Storage Complete")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Error storing in vector DB: {str(e)}")
            raise
    
    def step_4_test_retrieval(self, query: str = "Học sinh cấp 3 có được học bổng không?") -> None:
        """
        BƯỚC 4: Test tìm kiếm (optional)
        
        Args:
            query: Query string để test
        """
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STEP 4: TESTING RETRIEVAL (Optional)")
        logger.info("=" * 80)
        
        logger.info(f"\n❓ Query: {query}\n")
        
        results = self.vector_db.search_similar(query, k=3)
        
        if results:
            logger.info(f"✅ Found {len(results)} relevant documents:\n")
            for i, (doc, score) in enumerate(results, 1):
                logger.info(f"{i}. Score: {score:.4f}")
                logger.info(f"   Doc Type: {doc.metadata.get('doc_type')}")
                logger.info(f"   Content: {doc.page_content[:150]}...\n")
        else:
            logger.warning("⚠️  No results found")

    def step_5_discover_schema(self, config_path: str = "./config.yaml") -> bool:
        """
        BƯỚC 5: [v5 — Auto-Discovery] Phân tích tài liệu và sinh university_schema.yaml.

        Dùng LLM để:
        - Phân tích từng tài liệu JSON trong data/
        - Tự động xác định dimensions (ngành, khóa, v.v.)
        - Sinh ra university_schema.yaml cho IntentClassifier

        Args:
            config_path: Đường dẫn config.yaml

        Returns:
            True nếu thành công, False nếu lỗi.
        """
        logger.info("\n" + "=" * 80)
        logger.info("🔍 STEP 5: AUTO-DISCOVER INTENT SCHEMA")
        logger.info("=" * 80)

        try:
            from scripts.discover_schema import SchemaDiscoveryEngine, build_llm_invoker

            # Tái sử dụng LLM đã khởi tạo (tránh khởi tạo lại)
            llm_invoker = build_llm_invoker(self.config)

            engine = SchemaDiscoveryEngine(
                config=self.config,
                llm_invoker=llm_invoker,
                data_dir=self.output_path,
            )
            output_path = engine.discover()
            logger.info(f"\n✅ Schema đã được sinh tại: {output_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Lỗi khi discover schema: {e}")
            import traceback
            traceback.print_exc()
            logger.warning(
                "⚠️  Bỏ qua bước discover schema. "
                "Hệ thống sẽ fallback về intents trong config.yaml. "
                "Bạn có thể chạy thủ công: python scripts/discover_schema.py"
            )
            return False

    def run_full_pipeline(self, config_path: str = "./config.yaml") -> None:
        """
        Chạy toàn bộ pipeline 5 bước
        
        Args:
            config_path: Đường dẫn tới config.yaml
        """
        try:
            # Bước 1: Xử lý PDF
            pdf_count = self.step_1_process_pdfs(config_path)
            
            # Bước 2: Chunking
            chunk_count = self.step_2_chunk_documents(config_path)
            
            # Bước 3: Lưu vào Vector DB
            chunks = TextChunker.chunk_all_documents(self.output_path, config_path=config_path)
            self.step_3_store_in_vectordb(chunks)
            
            # Bước 4: Test retrieval
            self.step_4_test_retrieval()

            # Bước 5: [v5] Auto-Discover Intent Schema
            schema_ok = self.step_5_discover_schema(config_path)
            
            # Summary
            logger.info("\n" + "🎉" * 40)
            logger.info("PIPELINE EXECUTION COMPLETE!")
            logger.info(f"📊 Summary:")
            logger.info(f"   ✓ PDFs processed: {pdf_count}")
            logger.info(f"   ✓ Total chunks: {chunk_count}")
            logger.info(f"   ✓ Vector DB initialized: YES")
            logger.info(f"   ✓ Intent Schema discovered: {'YES ✅' if schema_ok else 'SKIPPED ⚠️ (fallback to config.yaml)'}")
            logger.info("🎉" * 40)
            
        except Exception as e:
            logger.error(f"\n❌ PIPELINE ERROR: {str(e)}")
            import traceback
            traceback.print_exc()


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    # Khởi tạo pipeline
    pipeline = DataPreparationPipelineRefactored(config_path="./config.yaml")
    
    # Chạy toàn bộ pipeline (bao gồm cả schema discovery)
    pipeline.run_full_pipeline(config_path="./config.yaml")
    
    # Hoặc chạy từng bước riêng lẻ:
    # pipeline.step_1_process_pdfs()
    # pipeline.step_2_chunk_documents()
    # chunks = TextChunker.chunk_all_documents(Path("./data"))
    # pipeline.step_3_store_in_vectordb(chunks)
    # pipeline.step_4_test_retrieval(query="Tiêu chí xét duyệt học bổng")
    # pipeline.step_5_discover_schema()  # [v5] Sinh schema tự động
