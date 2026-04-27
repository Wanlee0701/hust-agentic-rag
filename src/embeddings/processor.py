"""
Module xử lý dữ liệu từ PDF
Bao gồm: trích xuất text, xử lý bảng, tách chunks
"""
import json
import re
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import pdfplumber
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Xử lý PDF: trích xuất text, bảng, làm sạch dữ liệu"""
    
    @staticmethod
    def _load_cleanup_patterns(config_path: str = "./config.yaml") -> List[str]:
        """
        Load cleanup patterns từ config
        
        Args:
            config_path: Đường dẫn tới config.yaml
            
        Returns:
            List các regex patterns
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            patterns = config.get("pdf_processing", {}).get("text_cleanup_patterns", [])
            if patterns:
                return patterns
        except (FileNotFoundError, yaml.YAMLError):
            pass
        
        # Default patterns nếu config không tìm thấy
        return [
            r"^\d+\s*$",
            r"BỘ GIÁO DỤC VÀ ĐÀO TẠO",
            r"ĐẠI HỌC BÁCH KHOA HÀ NỘI",
            r"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            r"Độc lập - Tự do - Hạnh phúc",
            r"Ban hành kèm theo Quyết định số.*",
            r"HÀ NỘI,.*",
            r"Số:",
            r"Căn cứ",
            r"PGS.",
            r"KT.",
            r"PHÓ GIÁM ĐỐC",
            r"Nơi nhận:"
        ]
    
    @staticmethod
    def extract_pdf_text(text: str, cleanup_patterns: List[str] = None) -> str:
        """
        Làm sạch text từ PDF
        - Xóa header/footer, số trang, tên trường lặp lại
        - Format lại cấu trúc Markdown
        
        Args:
            text: Text thô từ PDF
            cleanup_patterns: List regex patterns (nếu None, load từ config)
            
        Returns:
            Text đã được làm sạch
        """
        if not text:
            return ""
        
        if cleanup_patterns is None:
            cleanup_patterns = PDFProcessor._load_cleanup_patterns()
        
        # Danh sách pattern cần xóa
        patterns_remove = cleanup_patterns
        
        # Xóa các pattern
        for pat in patterns_remove:
            text = re.sub(pat, '', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Format structure: Chương thành # Heading
        text = re.sub(r'(^|\n)(CHƯƠNG\s+[IVX0-9]+)', r'\1# \2', text)
        # Format structure: Điều thành ## Heading
        text = re.sub(r'(^|\n)(Điều\s+\d+\.)', r'\1## \2', text)
        
        return text.strip()
    
    @staticmethod
    def extract_tables_as_markdown(page) -> str:
        """
        Trích xuất bảng từ trang PDF và convert sang Markdown
        
        Args:
            page: Trang PDF (pdfplumber page object)
            
        Returns:
            Markdown string của các bảng
        """
        tables = page.extract_tables()
        if not tables:
            return ""
        
        md_tables = []
        for table in tables:
            df = pd.DataFrame(table)
            # Xóa dòng/cột trống
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if not df.empty:
                md = df.to_markdown(index=False)
                md_tables.append(md)
        
        return "\n\n".join(md_tables)
    
    @staticmethod
    def process_pdf_file(pdf_path: str, config_path: str = "./config.yaml") -> str:
        """
        Xử lý toàn bộ file PDF
        - Trích xuất text từ mỗi trang
        - Xử lý bảng
        - Làm sạch dữ liệu
        
        Args:
            pdf_path: Đường dẫn tới file PDF
            config_path: Đường dẫn tới config.yaml
            
        Returns:
            Toàn bộ nội dung PDF sau xử lý
        """
        full_content = []
        
        try:
            cleanup_patterns = PDFProcessor._load_cleanup_patterns(config_path)
            
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # Trích xuất text
                    text = page.extract_text() or ""
                    
                    # Trích xuất bảng
                    table_md = PDFProcessor.extract_tables_as_markdown(page)
                    
                    # Làm sạch text
                    cleaned_text = PDFProcessor.extract_pdf_text(text, cleanup_patterns)
                    
                    # Ghép text và bảng
                    page_content = cleaned_text
                    if table_md:
                        page_content += "\n\n[Bảng Biểu]:\n" + table_md
                    
                    full_content.append(page_content)
            
            logger.info(f"✅ Processed PDF: {Path(pdf_path).name} ({len(pdf.pages)} pages)")
            return "\n\n".join(full_content)
            
        except Exception as e:
            logger.error(f"❌ Error processing PDF {pdf_path}: {str(e)}")
            return ""


class TextChunker:
    """Tách text thành chunks, giữ lại cấu trúc và bảng"""
    
    @staticmethod
    def split_text_keeping_tables(text: str, chunk_size: int = 1000, 
                                  chunk_overlap: int = 200) -> List[str]:
        """
        Tách text nhưng giữ nguyên bảng
        - Tìm bảng trong text
        - Tách text thành chunks
        - Gữ nguyên bảng không bị tách
        
        Args:
            text: Text cần tách
            chunk_size: Kích thước mỗi chunk
            chunk_overlap: Overlap giữa các chunks
            
        Returns:
            List các chunks
        """
        # Pattern để detect bảng Markdown
        table_pattern = r'(?:\|.*\|\n\|[-:| ]+\|\n(?:\|.*\|\n?)*)'
        
        # Khởi tạo text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Tìm tất cả bảng
        tables = list(re.finditer(table_pattern, text))
        
        # Nếu không có bảng, split bình thường
        if not tables:
            return text_splitter.split_text(text)
        
        # Xử lý text với bảng
        final_chunks = []
        last_end = 0
        
        for match in tables:
            start, end = match.span()
            
            # Xử lý text TRƯỚC bảng
            pre_table_text = text[last_end:start]
            if pre_table_text.strip():
                final_chunks.extend(text_splitter.split_text(pre_table_text))
            
            # Giữ nguyên bảng (không tách)
            table_text = match.group()
            final_chunks.append(table_text)
            
            last_end = end
        
        # Xử lý text SAU bảng cuối cùng
        post_table_text = text[last_end:]
        if post_table_text.strip():
            final_chunks.extend(text_splitter.split_text(post_table_text))
        
        return final_chunks
    
    @staticmethod
    def chunk_json_document(json_path: Path, chunk_size: int = 1000,
                           chunk_overlap: int = 200,
                           config_path: str = "./config.yaml") -> List[Document]:
        """
        Tách document JSON thành chunks (Documents)
        - Load JSON file
        - Tách theo structure Markdown (Chương/Điều)
        - Gắn metadata cho mỗi chunk
        
        Args:
            json_path: Đường dẫn tới JSON file
            chunk_size: Kích thước chunk (nếu 0, load từ config)
            chunk_overlap: Overlap (nếu 0, load từ config)
            config_path: Đường dẫn tới config.yaml
            
        Returns:
            List Document objects với page_content và metadata
        """
        # Load chunk settings từ config nếu không chỉ định
        if chunk_size == 0 or chunk_overlap == 0:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                chunking_config = config.get("chunking", {})
                chunk_size = chunk_size or chunking_config.get("chunk_size", 1000)
                chunk_overlap = chunk_overlap or chunking_config.get("chunk_overlap", 200)
            except (FileNotFoundError, yaml.YAMLError):
                chunk_size = chunk_size or 1000
                chunk_overlap = chunk_overlap or 200
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"❌ Error loading JSON {json_path}: {str(e)}")
            return []
        
        # Headers để split theo cấu trúc
        header_to_split_on = [
            ("#", "chapter_title"),
            ("##", "article_title"),
        ]
        
        # Khởi tạo splitters
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=header_to_split_on
        )
        
        # Lấy metadata gốc từ JSON
        base_metadata = data['metadata']
        content = data['content']
        
        # BƯỚC 1: Tách theo Markdown headers
        md_header_splits = markdown_splitter.split_text(content)
        
        # BƯỚC 2: Tách tiếp theo kích thước chunk, gắn metadata
        final_chunks = []
        
        for split in md_header_splits:
            content_of_article = split.page_content
            metadata_of_article = split.metadata
            
            # Tách nhỏ hơn nữa, giữ bảng
            sub_chunks = TextChunker.split_text_keeping_tables(
                content_of_article,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # Gắn metadata cho mỗi chunk
            for chunk_text in sub_chunks:
                is_table = chunk_text.strip().startswith("|")
                
                combined_metadata = {
                    **base_metadata,          # Metadata gốc
                    **metadata_of_article,    # Chapter/Article info
                    "is_table": is_table      # Flag để phân biệt bảng
                }
                
                doc = Document(
                    page_content=chunk_text,
                    metadata=combined_metadata
                )
                final_chunks.append(doc)
        
        logger.info(f"✅ Chunked {json_path.name}: {len(final_chunks)} chunks")
        return final_chunks
    
    @staticmethod
    def chunk_all_documents(data_path: Path, chunk_size: int = 0,
                           chunk_overlap: int = 0,
                           config_path: str = "./config.yaml") -> List[Document]:
        """
        Tách tất cả JSON documents
        
        Args:
            data_path: Đường dẫn thư mục chứa JSON files
            chunk_size: Kích thước chunk (0 = load từ config)
            chunk_overlap: Overlap (0 = load từ config)
            config_path: Đường dẫn tới config.yaml
            
        Returns:
            List tất cả Document objects
        """
        # Load từ config nếu không chỉ định
        if chunk_size == 0 or chunk_overlap == 0:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                chunking_config = config.get("chunking", {})
                chunk_size = chunk_size or chunking_config.get("chunk_size", 1000)
                chunk_overlap = chunk_overlap or chunking_config.get("chunk_overlap", 200)
            except (FileNotFoundError, yaml.YAMLError):
                chunk_size = chunk_size or 1000
                chunk_overlap = chunk_overlap or 200
        
        json_files = list(data_path.glob('*.json'))
        
        logger.info("=" * 80)
        logger.info(f"🔀 STARTING DOCUMENT CHUNKING")
        logger.info(f"📊 Found {len(json_files)} JSON files")
        logger.info(f"📋 Config: chunk_size={chunk_size}, overlap={chunk_overlap}")
        logger.info("=" * 80)
        
        all_chunks = []
        
        for json_file in json_files:
            try:
                chunks = TextChunker.chunk_json_document(
                    json_file,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    config_path=config_path
                )
                all_chunks.extend(chunks)
                
                # Thống kê
                table_chunks = sum(1 for c in chunks if c.metadata.get("is_table"))
                text_chunks = len(chunks) - table_chunks
                
                logger.info(f"  ✅ {json_file.name}: {len(chunks)} chunks "
                           f"(text: {text_chunks}, tables: {table_chunks})")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing {json_file.name}: {str(e)}")
        
        logger.info("=" * 80)
        logger.info(f"✨ TOTAL CHUNKS: {len(all_chunks)}")
        logger.info("=" * 80)
        
        return all_chunks
    
    @staticmethod
    def save_chunks_to_json(chunks: List[Document], output_path: Path,
                           file_name: str) -> None:
        """
        Lưu chunks vào file JSON
        
        Args:
            chunks: List Document objects
            output_path: Đường dẫn thư mục output
            file_name: Tên file output
        """
        output_file = output_path / file_name
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [c.dict() for c in chunks],
                    f,
                    ensure_ascii=False,
                    indent=4
                )
            logger.info(f"✅ Saved chunks to {output_file}")
        except Exception as e:
            logger.error(f"❌ Error saving chunks: {str(e)}")
            raise
