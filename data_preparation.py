import json
import os
import re
from pathlib import Path
import pandas as pd
import pdfplumber
import logging
import tabulate
from datetime import datetime
from typing import Dict, Any, List, Any, Optional, Tuple
from langchain_chroma import Chroma
import chromadb
# from langdetect import detect
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
class DataPreparationPipeline:
    def __init__(self, kb_path: str="./knowledge_base/raw", output_path: str="./data"):
        self.kb_path = Path(kb_path)
        self.output_path = Path(output_path)
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")
        self.output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized DataPreparationPipeline with kb_path: {kb_path} and output_path: {output_path}")
        self.metadata_mapping = self.__init__metadata_mapping()
    
    @staticmethod
    def __init__metadata_mapping() -> Dict[str, Dict[str, str]]:
        return {
            "HD_hoc_chuyen_tiep_ky_su_180TC.pdf": {
                "doc_type": "Hướng dẫn chuyển tiếp kỹ sư",
                "effective_date": "2025-05-28",
                "applicable_students": "ALL",
                "status": "active"
            },
            "Quy_che_25.pdf": {
                "doc_type": "Quy chế đào tạo",
                "effective_date": "2025-05-28",
                "applicable_students": "ALL",
                "status": "active"
            },
            "Quy_che_CTSV_ĐHBK_HN_2025310_final.pdf": {
                "doc_type": "Quy chế công tác sinh viên",
                "effective_date": "2025-03-10",
                "applicable_students": "All",
                "status": "active"
            },
            "Hoc_bong_TDN_2023.pdf": {
                "doc_type": "QĐ Học bổng Trần Đại Nghĩa",
                "effective_date": "2023",
                "applicable_students": "All",
                "status": "active"
            },
            "Hoc_bong_KKHT_2023.pdf": {
                "doc_type": "QĐ Học bổng KKHT",
                "effective_date": "2023",
                "applicable_students": "All",
                "status": "active"
            },
            "QD_NN_K68.pdf": {
                "doc_type": "Quyết định ngoại ngữ K68",
                "effective_date": "2024",
                "applicable_students": ">=K68",
                "status": "active"
            },
            "QD_NN_K70.pdf": {
                "doc_type": "Quyết định ngoại ngữ K70",
                "effective_date": "2025",
                "applicable_students": ">= K70",
                "status": "active"
            },
            "QD_NN_K65.pdf": {
                "doc_type": "Quyết định ngoại ngữ K65",
                "effective_date": "2020",
                "applicable_students": ">= K65",
                "status": "active"
            },
            "QD_chuyen_doi_hoc_phan_tuong_duong.pdf": {
                "doc_type": "QĐ Chuyển đổi học phần tương đương",
                "effective_date": "2021",
                "applicable_students": "All",
                "status": "active"
            },
        }

    @staticmethod
    def extract_pdf(text: str) -> str:
        if not text: return ""
    # 1. Xóa Header/Footer, Số trang, Tên trường lặp lại
        patterns_remove = [
            r"^\d+\s*$", # Số trang đứng một mình
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
        for pat in patterns_remove:
            text = re.sub(pat, '', text, flags=re.MULTILINE | re.IGNORECASE)

        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'(^|\n)(CHƯƠNG\s+[IVX0-9]+)', r'\1# \2', text)
        text = re.sub(r'(^|\n)(Điều\s+\d+\.)', r'\1## \2', text)

        return text.strip()

    @staticmethod
    def extract_table_to_md(page) -> str:
        tables = page.extract_tables()
        md_tables = []
        for table in tables:
            df =pd.DataFrame(table)
            df = df.dropna(how='all').dropna(axis=1, how='all')

            if not df.empty:
                md = df.to_markdown(index=False)
                md_tables.append(md)
        return "\n\n".join(md_tables)

    def process_pdf(self, pdf_path, pdf_name) -> str:
        full_content = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    table_md = self.extract_table_to_md(page)
                    cleaned_text = self.extract_pdf(text)
                    page_content = cleaned_text
                    if table_md:
                        page_content += "\n\n [Bảng Biểu]:\n" + table_md
                    full_content.append(page_content)
            return "\n\n".join(full_content)
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_name}: {str(e)}")
            return ""

    def run_etl_pipeline(self) -> int:
        logger.info("="*50)
        logger.info("Starting ETL pipeline...")
        logger.info("="*50)
        process_count = 0
        files = [
            f for f in os.listdir(self.kb_path) if f.lower().endswith('.pdf')
        ]

        logger.info(f"Found {len(files)} PDF files in {self.kb_path}")

        for file in files:
            file_path = self.kb_path / file
            meta = self.metadata_mapping.get(file, {
                "doc_type": "Unknown",
                "effective_date": "Unknown",
                "applicable_students": "Unknown",
                "status": "Unknown"
            })
            meta['source_file'] = file
            meta['processed_date'] = datetime.now().isoformat()
            logger.info(f"Processing file: {file} with metadata: {meta}")
            content = self.process_pdf(file_path, file)
            if content:
                document_object = {
                    "metadata": meta,
                    "content": content
                }
                output_file = self.output_path / f"{Path(file).stem}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(document_object, f, ensure_ascii=False, indent=4)
                logger.info(f"Successfully processed and saved: {output_file}")
                process_count += 1
            else:
                logger.warning(f"No content extracted from {file}")
        logger.info("="*50)
        logger.info(f"ETL pipeline completed. Total files processed: {process_count}")
        logger.info("="*50)
        return process_count
    @staticmethod
    def split_text_keeping_tables(text: str) -> List[str]:
        header_to_split_on = [
            ("#", "chapter_title"),
            ("##", "article_title"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=header_to_split_on)
        text_recursive = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        # Detect table
        table_pattern = r'(?:\|.*\|\n\|[-:| ]+\|\n(?:\|.*\|\n?)*)'
        tables = list(re.finditer(table_pattern, text))
        if not tables:
            return text_recursive.split_text(text)
        final_chunks = []
        last_end = 0

        for match in tables:
            start, end = match.span()

            # 1. XỬ LÝ PHẦN VĂN BẢN TRƯỚC BẢNG
            pre_table_text = text[last_end:start]
            if pre_table_text.strip():
                final_chunks.extend(text_recursive.split_text(pre_table_text))

            # 2. XỬ LÝ PHẦN BẢNG (GIỮ NGUYÊN)
            table_text = match.group()
            if len(table_text) > 4000:
                final_chunks.append(table_text)
            else:
                final_chunks.append(table_text)
            last_end = end

        # 3. XỬ LÝ PHẦN VĂN BẢN CÒN LẠI SAU BẢNG CUỐI
        post_table_text = text[last_end:]
        if post_table_text.strip():
            final_chunks.extend(text_recursive.split_text(post_table_text))

        return final_chunks  

    def chunk_json_file(self, json_path: Path) -> List[Document]:
        with open(json_path, 'r', encoding='utf-8') as f:
          data = json.load(f)
        header_to_split_on = [
            ("#", "chapter_title"),
            ("##", "article_title"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=header_to_split_on)
        text_recursive = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        # Lấy Metadata gốc (Cực kỳ quan trọng)
        base_metadata = data['metadata']
        content = data['content']

        # BƯỚC 1: Cắt theo cấu trúc Markdown (Chương/Điều)
        md_header_splits = markdown_splitter.split_text(content)
        final_chunks = []

        # BƯỚC 2: Kiểm tra độ dài và Gắn Metadata gốc
        for split in md_header_splits:
            content_of_article = split.page_content
            metadata_of_article = split.metadata
            sub_chunks = self.split_text_keeping_tables(content_of_article)
            for chunk_text in sub_chunks:
                # Kiểm tra xem chunk này có phải là bảng không để gán nhãn (Optional)
                is_table = chunk_text.strip().startswith("|")

                combined_metadata = {
                    **base_metadata,
                    **metadata_of_article,
                    "is_table": is_table # Thêm cờ này để sau này dễ lọc
                }

                doc = Document(
                    page_content=chunk_text,
                    metadata=combined_metadata
                )
                final_chunks.append(doc)
        return final_chunks
    def chunk_all_documents(self) -> None:
        logger.info("="*80)
        logger.info("🔀 STARTING DOCUMENT CHUNKING")
        logger.info("="*80 + "\n")
        
        json_files = list(self.output_path.glob('*.json'))
        logger.info(f"📊 Found {len(json_files)} JSON files\n")
        
        total_chunks = 0
        all_final_chunks = []
        for json_file in json_files:
            logger.info(f"⏳ Chunking: {json_file.name}")
            
            try:
                chunks = self.chunk_json_file(json_file)
                all_final_chunks.extend(chunks)
                table_chunks = sum(
                    1 for c in chunks
                    if c.metadata.get("is_table")
                )
                text_chunks = len(chunks) - table_chunks
                
                logger.info(f"  ✅ Created {len(chunks)} chunks")
                logger.info(f"     • Text: {text_chunks}")
                logger.info(f"     • Tables: {table_chunks}\n")
                
                total_chunks += len(chunks)
                all_chunks_output = self.output_path / "chunks" / f"{json_file.stem}_chunks.json"
                self.output_path.joinpath("chunks").mkdir(exist_ok=True)
                with open(all_chunks_output, 'w', encoding='utf-8') as f:
                    json.dump(
                        [c.dict() for c in chunks],
                        f,
                        ensure_ascii=False,
                        indent=4
                    ) 
            except Exception as e:
                logger.error(f"  ❌ Error: {str(e)}\n")
        
        logger.info("="*80)
        logger.info(f"✨ CHUNKING COMPLETE: {total_chunks} total chunks")
        logger.info("="*80 + "\n")
        return all_final_chunks

    # Store chunks in vector database (Chroma)
    def store_in_vector_db(self, chunks):
        persistent_client = chromadb.PersistentClient(path=str(os.path.join(self.output_path, "chroma")))
        vector_db_path = self.output_path / "chroma"
        vectorstore = Chroma(
            embedding_function=self.embeddings,
            collection_name="student_regulations",
            persist_directory=vector_db_path,
        )
        vectorstore.add_documents(chunks)
        # vectorstore.persist()
        logger.info(f"✅ Stored {len(chunks)} chunks in vector database at {vector_db_path}")
    def run(self) -> None:
        try:
            # 1️⃣ ETL Pipeline
            etl_count = self.run_etl_pipeline()
            
            # 2️⃣ Chunking
            all_chunks = self.chunk_all_documents()
            
            # 3️⃣Store in Vector DB
            self.store_in_vector_db(all_chunks)
            # ✨ Summary
            json_count = len(list(self.output_path.glob('*.json')))
            logger.info("🎉 PIPELINE COMPLETE!")
            logger.info(f"📊 Results:")
            logger.info(f"  • JSON files: {json_count} documents")
            logger.info(f"  • Ready for embeddings & vectordb\n")
        
        except Exception as e:
            logger.error(f"\n❌ PIPELINE ERROR: {str(e)}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Khởi tạo pipeline
    pipeline = DataPreparationPipeline()
    
    # Chạy toàn bộ pipeline
    pipeline.run()
