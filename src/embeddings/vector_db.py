"""
Module quản lý vector database (Chroma)
Bao gồm: khởi tạo DB, lưu documents, tìm kiếm
"""
import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class VectorDatabaseManager:
    """Quản lý vector database (Chroma)"""
    
    def __init__(self, 
                 embeddings: HuggingFaceEmbeddings,
                 persist_directory: str = None,
                 collection_name: str = None,
                 config_path: str = "./config.yaml"):
        """
        Khởi tạo VectorDatabaseManager
        
        Args:
            embeddings: HuggingFaceEmbeddings model
            persist_directory: Đường dẫn lưu Chroma DB (optional, từ config nếu không chỉ định)
            collection_name: Tên collection (optional, từ config nếu không chỉ định)
            config_path: Đường dẫn tới config.yaml
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            self.config = {}
        
        vectordb_config = self.config.get("vectordb", {})
        retrieval_config = self.config.get("retrieval", {})
        
        self.embeddings = embeddings
        self.persist_directory = Path(
            persist_directory or
            vectordb_config.get("persist_directory", "./data/chroma")
        )
        self.collection_name = (
            collection_name or
            vectordb_config.get("collection_name", "student_regulations")
        )
        self.retrieval_config = retrieval_config
        
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """
        Khởi tạo Chroma database
        - Tạo thư mục nếu chưa tồn tại
        - Kết nối tới Chroma client
        - Tạo hoặc load collection
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🔄 Initializing Chroma vector database")
            logger.info(f"   Path: {self.persist_directory}")
            logger.info(f"   Collection: {self.collection_name}")
            
            # Khởi tạo persistent client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory)
            )
            
            # Tạo hoặc load vectorstore
            self.vectorstore = Chroma(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=str(self.persist_directory),
                client=self.client
            )
            
            logger.info(f"✅ Vector database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing vector database: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Document]) -> int:
        """
        Thêm documents vào vector database
        - Documents được embedding
        - Lưu vào Chroma DB
        
        Args:
            documents: List Document objects
            
        Returns:
            Số lượng documents được thêm
        """
        if not documents:
            logger.warning("⚠️  No documents to add")
            return 0
        
        try:
            logger.info(f"📥 Adding {len(documents)} documents to vector database...")
            
            # Add documents tới vectorstore
            doc_ids = self.vectorstore.add_documents(documents)
            
            logger.info(f"✅ Successfully added {len(doc_ids)} documents")
            logger.info(f"   Collection now contains approximately {len(doc_ids)} vectors")
            
            return len(doc_ids)
            
        except Exception as e:
            logger.error(f"❌ Error adding documents: {str(e)}")
            raise
    
    def search_similar(self, query: str, k: int = None, 
                       score_threshold: float = None) -> List[tuple]:
        """
        Tìm kiếm documents tương tự
        
        Args:
            query: Query string
            k: Số lượng kết quả (nếu None, dùng top_k từ config)
            score_threshold: Ngưỡng similarity score (nếu None, dùng từ config)
            
        Returns:
            List tuples: (Document, similarity_score)
        """
        try:
            # Dùng config nếu không chỉ định parameter
            if k is None:
                k = self.retrieval_config.get("top_k", 5)
            
            if score_threshold is None:
                score_threshold = self.retrieval_config.get("similarity_threshold", 0.5)
            
            logger.debug(f"🔍 Searching for: {query} (k={k}, threshold={score_threshold})")
            
            # Tìm kiếm tương tự
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            # Filter theo threshold nếu cần
            if score_threshold > 0:
                results = [(doc, score) for doc, score in results 
                          if score >= score_threshold]
            
            logger.debug(f"✅ Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching: {str(e)}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin về collection
        
        Returns:
            Dictionary chứa thông tin collection
        """
        try:
            collection = self.client.get_collection(
                name=self.collection_name
            )
            
            info = {
                "collection_name": self.collection_name,
                "count": collection.count(),
                "persist_directory": str(self.persist_directory)
            }
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Error getting collection info: {str(e)}")
            return {}
    
    def delete_collection(self) -> bool:
        """
        Xóa collection (cẩn thận!)
        
        Returns:
            True nếu xóa thành công
        """
        try:
            logger.warning(f"⚠️  Deleting collection: {self.collection_name}")
            
            self.client.delete_collection(
                name=self.collection_name
            )
            
            # Reinitialize vectorstore
            self.vectorstore = Chroma(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=str(self.persist_directory),
                client=self.client
            )
            
            logger.info(f"✅ Collection deleted and reset")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {str(e)}")
            return False
    
    def export_collection_metadata(self, output_path: str) -> bool:
        """
        Export metadata của collection
        
        Args:
            output_path: Đường dẫn lưu file metadata
            
        Returns:
            True nếu export thành công
        """
        try:
            import json
            
            collection = self.client.get_collection(
                name=self.collection_name
            )
            
            metadata = {
                "collection_name": self.collection_name,
                "document_count": collection.count(),
                "persist_directory": str(self.persist_directory),
                "embedding_model": "HuggingFace"
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            
            logger.info(f"✅ Collection metadata exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error exporting metadata: {str(e)}")
            return False
    
    def persist(self) -> None:
        """
        Lưu trữ vectorstore (nếu cần)
        Chroma tự động lưu, nhưng method này để chắc chắn
        """
        try:
            if hasattr(self.vectorstore, 'persist'):
                self.vectorstore.persist()
                logger.info("✅ Vector database persisted")
        except Exception as e:
            logger.warning(f"⚠️  Error persisting: {str(e)}")
