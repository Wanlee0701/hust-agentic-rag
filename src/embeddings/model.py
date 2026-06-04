"""
Module quản lý embeddings model
Đọc cấu hình từ config.yaml và load mô hình embedding
"""
import yaml
import logging
from typing import Dict, Any
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingModelManager:
    """Quản lý việc load và cấu hình embedding model"""
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Khởi tạo EmbeddingModelManager
        
        Args:
            config_path: Đường dẫn tới file config.yaml
        """
        self.config = self._load_config(config_path)
        self.embedding_config = self.config.get("embedding", {})
        self.model = None
        self._initialize_model()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Đọc file config.yaml
        
        Args:
            config_path: Đường dẫn tới file config
            
        Returns:
            Dictionary chứa cấu hình
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Loaded config from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"❌ Config file not found at {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"❌ Error parsing YAML config: {str(e)}")
            raise
    
    def _initialize_model(self) -> None:
        """
        Khởi tạo embedding model từ HuggingFace
        dựa trên cấu hình trong config.yaml
        """
        try:
            model_name = self.embedding_config.get("model_name", "BAAI/bge-m3")
            cache_folder = self.embedding_config.get("cache_folder")
            batch_size = self.embedding_config.get("batch_size", 32)
            
            logger.info(f"🔄 Initializing embedding model: {model_name}")
            logger.info(f"   Cache folder: {cache_folder if cache_folder else 'System Default (C drive)'}")
            logger.info(f"   Batch size: {batch_size}")
            
            # Tạo cache folder nếu được chỉ định
            if cache_folder:
                Path(cache_folder).mkdir(parents=True, exist_ok=True)
            
            # Load model từ HuggingFace
            kwargs = {"model_name": model_name, "encode_kwargs": {"batch_size": batch_size}}
            if cache_folder:
                kwargs["cache_folder"] = cache_folder
                
            self.model = HuggingFaceEmbeddings(**kwargs)
            
            logger.info(f"✅ Embedding model loaded successfully")
            logger.info(f"   Model dimension: {self.embedding_config.get('dimension', 'N/A')}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing embedding model: {str(e)}")
            raise
    
    def get_model(self) -> HuggingFaceEmbeddings:
        """
        Trả về embedding model đã được load
        
        Returns:
            HuggingFaceEmbeddings model
        """
        if self.model is None:
            raise RuntimeError("Embedding model not initialized")
        return self.model
    
    def get_config(self) -> Dict[str, Any]:
        """
        Trả về toàn bộ cấu hình
        
        Returns:
            Dictionary chứa cấu hình
        """
        return self.config
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """
        Trả về phần cấu hình embedding
        
        Returns:
            Dictionary chứa embedding config
        """
        return self.embedding_config
