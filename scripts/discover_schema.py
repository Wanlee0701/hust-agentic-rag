"""
discover_schema.py — SchemaDiscoveryEngine: Tự động phân tích tài liệu và sinh university_schema.yaml

Sử dụng:
    python scripts/discover_schema.py
    python scripts/discover_schema.py --config ./config.yaml --output ./university_schema.yaml

Quy trình:
    1. Đọc sample từ mỗi file JSON trong data/
    2. Gọi LLM phân tích: "Thông tin nào phụ thuộc vào ngành/khóa/đối tượng?"
    3. Tổng hợp kết quả → sinh intents + domain_entities
    4. Ghi ra university_schema.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Fix path để import src khi chạy từ bất kỳ thư mục nào
sys.path.append(str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Prompt Templates
# ============================================================================

_ANALYZE_DOC_PROMPT = """\
Bạn là chuyên gia phân tích tài liệu giáo dục đại học.

Tài liệu sau là một phần nội dung quy chế/quy định của một trường đại học:
---
{doc_sample}
---

Nhiệm vụ: Phân tích xem trong tài liệu này:
1. Có những loại thông tin nào PHỤ THUỘC vào ngành học, khóa học, hoặc đối tượng sinh viên cụ thể không?
   (Ví dụ: học phí khác nhau theo ngành; chuẩn ngoại ngữ khác nhau theo khóa)
2. Nếu có, liệt kê các "dimension" (chiều thông tin) cần thiết để tra cứu chính xác.
3. Nếu KHÔNG có thông tin phụ thuộc → ghi dimension_required = false.

Trả về JSON (KHÔNG giải thích thêm):
{{
  "doc_summary": "Tóm tắt ngắn nội dung tài liệu (1-2 câu)",
  "topic_group": "Nhóm chủ đề chính: GENERAL_REGULATION | TUITION_FEE | LANGUAGE_REQUIREMENT | SCHOLARSHIP | ACADEMIC_DISCIPLINE | OTHER",
  "dimension_required": true/false,
  "dimensions": [
    {{
      "name": "tên_entity (snake_case, tiếng Việt không dấu)",
      "label": "Nhãn hiển thị cho người dùng",
      "description": "Mô tả entity",
      "examples": ["Ví dụ 1", "Ví dụ 2", "Ví dụ 3"],
      "clarification_prompt": "Câu hỏi làm rõ khi thiếu entity này"
    }}
  ],
  "example_questions": ["Câu hỏi ví dụ 1", "Câu hỏi ví dụ 2"]
}}"""

_SYNTHESIZE_PROMPT = """\
Bạn là kiến trúc sư hệ thống chatbot giáo dục đại học.

Dưới đây là kết quả phân tích từ {n_docs} tài liệu của một trường đại học:
---
{analysis_results}
---

Nhiệm vụ: Tổng hợp thành một schema intent hoàn chỉnh cho hệ thống chatbot.

Yêu cầu:
- Gom các tài liệu cùng chủ đề vào một intent
- Mỗi intent có tên UPPER_SNAKE_CASE
- Hợp nhất các dimensions trùng lặp (cùng tên entity)
- Sinh clarification_template đầy đủ cho mỗi intent có requires_entities=true
- Tên entity phải nhất quán (dùng snake_case tiếng Việt không dấu)

Trả về JSON (KHÔNG giải thích):
{{
  "university_name": "Tên trường (suy ra từ nội dung, nếu không rõ dùng 'University Chatbot')",
  "intents": [
    {{
      "name": "INTENT_NAME",
      "description": "Mô tả intent",
      "requires_entities": true/false,
      "required_fields": ["entity1", "entity2"],
      "clarification_template": "Template câu hỏi làm rõ (multiline OK)",
      "examples": ["Câu hỏi ví dụ 1", "Câu hỏi ví dụ 2", "Câu hỏi ví dụ 3"]
    }}
  ],
  "domain_entities": [
    {{
      "name": "entity_name",
      "description": "Mô tả entity",
      "examples": ["ví dụ 1", "ví dụ 2", "ví dụ 3"],
      "clarification_prompt": "Câu hỏi khi thiếu entity này",
      "discovered_from": ["file1.json", "file2.json"]
    }}
  ]
}}"""


# ============================================================================
# SchemaDiscoveryEngine
# ============================================================================

class SchemaDiscoveryEngine:
    """
    Tự động phân tích tài liệu và sinh university_schema.yaml.

    Sử dụng LLM để:
    1. Phân tích từng tài liệu → xác định dimensions cần thiết.
    2. Tổng hợp toàn bộ → sinh intent schema hoàn chỉnh.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        llm_invoker,  # Callable[[str], str]
        data_dir: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ):
        self._config = config
        self._llm = llm_invoker
        self._schema_cfg = config.get("schema", {})

        # Data directory
        data_paths = config.get("data_paths", {})
        self._data_dir = data_dir or Path(data_paths.get("output_base", "./data"))
        self._output_path = output_path or Path(
            self._schema_cfg.get("schema_path", "./university_schema.yaml")
        )
        self._sample_chars = self._schema_cfg.get("sample_chars_per_doc", 3000)

    # ----------------------------------------------------------------------- #
    #  Public                                                                   #
    # ----------------------------------------------------------------------- #

    def discover(self) -> Path:
        """
        Chạy full pipeline discovery.
        Returns:
            Path đến university_schema.yaml đã được tạo.
        """
        logger.info("=" * 70)
        logger.info("🔍 SCHEMA DISCOVERY ENGINE — BẮT ĐẦU")
        logger.info("=" * 70)

        # 1. Quét tài liệu JSON
        json_files = self._scan_json_files()
        if not json_files:
            logger.error(f"❌ Không tìm thấy file JSON nào trong {self._data_dir}")
            raise FileNotFoundError(f"No JSON files found in {self._data_dir}")

        logger.info(f"📂 Tìm thấy {len(json_files)} tài liệu JSON")

        # 2. Phân tích từng tài liệu
        analysis_results = []
        for i, json_file in enumerate(json_files, 1):
            logger.info(f"\n[{i}/{len(json_files)}] 📄 Phân tích: {json_file.name}")
            result = self._analyze_document(json_file)
            if result:
                result["source_file"] = json_file.name
                analysis_results.append(result)
                logger.info(
                    f"   ✅ Topic: {result.get('topic_group')} | "
                    f"Dimensions: {len(result.get('dimensions', []))}"
                )
            else:
                logger.warning(f"   ⚠️  Bỏ qua (phân tích thất bại)")

        if not analysis_results:
            raise RuntimeError("Không phân tích được tài liệu nào.")

        # 3. Tổng hợp toàn bộ → schema
        logger.info(f"\n{'='*70}")
        logger.info(f"🔄 TỔNG HỢP SCHEMA từ {len(analysis_results)} tài liệu...")
        logger.info(f"{'='*70}")
        schema = self._synthesize_schema(analysis_results)

        # 4. Ghi file
        self._write_schema(schema, analysis_results)

        logger.info(f"\n{'='*70}")
        logger.info(f"✅ HOÀN THÀNH! Schema đã được ghi vào: {self._output_path}")
        logger.info(f"   Intents: {len(schema.get('intents', []))}")
        logger.info(f"   Domain entities: {len(schema.get('domain_entities', []))}")
        logger.info(f"{'='*70}")

        return self._output_path

    # ----------------------------------------------------------------------- #
    #  Step 1: Scan files                                                       #
    # ----------------------------------------------------------------------- #

    def _scan_json_files(self) -> List[Path]:
        """Lấy danh sách file JSON trong data_dir (bỏ qua thư mục con)."""
        if not self._data_dir.exists():
            return []
        return sorted([
            f for f in self._data_dir.iterdir()
            if f.is_file() and f.suffix.lower() == ".json"
        ])

    # ----------------------------------------------------------------------- #
    #  Step 2: Analyze each document                                            #
    # ----------------------------------------------------------------------- #

    def _analyze_document(self, json_file: Path) -> Optional[Dict[str, Any]]:
        """Phân tích một tài liệu JSON, trả về dict kết quả."""
        try:
            sample = self._extract_sample(json_file)
            if not sample:
                return None

            prompt = _ANALYZE_DOC_PROMPT.format(doc_sample=sample)
            raw = self._llm(prompt)
            result = self._parse_json_response(raw)
            return result
        except Exception as e:
            logger.warning(f"   ❌ Lỗi phân tích {json_file.name}: {e}")
            return None

    def _extract_sample(self, json_file: Path) -> str:
        """Đọc sample text đại diện từ file JSON."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Hỗ trợ cả hai cấu trúc: {"content": "..."} và {"metadata": {}, "content": "..."}
        content = ""
        if isinstance(data, dict):
            content = data.get("content", "")
            if not content:
                # Nếu không có key 'content', nối tất cả string values
                content = " ".join(
                    str(v) for v in data.values()
                    if isinstance(v, str) and len(v) > 50
                )
        elif isinstance(data, list):
            # Nếu là list of chunks
            content = " ".join(
                item.get("page_content", item.get("content", ""))
                if isinstance(item, dict) else str(item)
                for item in data[:20]
            )

        return content[:self._sample_chars]

    # ----------------------------------------------------------------------- #
    #  Step 3: Synthesize schema                                                #
    # ----------------------------------------------------------------------- #

    def _synthesize_schema(self, analysis_results: List[Dict]) -> Dict[str, Any]:
        """Gọi LLM tổng hợp kết quả phân tích thành schema hoàn chỉnh."""
        # Build analysis summary text
        summaries = []
        for r in analysis_results:
            summary = (
                f"File: {r.get('source_file', 'unknown')}\n"
                f"Tóm tắt: {r.get('doc_summary', '')}\n"
                f"Nhóm chủ đề: {r.get('topic_group', 'OTHER')}\n"
                f"Cần dimensions: {r.get('dimension_required', False)}\n"
            )
            if r.get("dimensions"):
                dims = json.dumps(r["dimensions"], ensure_ascii=False, indent=2)
                summary += f"Dimensions: {dims}\n"
            if r.get("example_questions"):
                summary += f"Câu hỏi ví dụ: {r['example_questions']}\n"
            summaries.append(summary)

        analysis_text = "\n---\n".join(summaries)
        prompt = _SYNTHESIZE_PROMPT.format(
            n_docs=len(analysis_results),
            analysis_results=analysis_text[:6000],  # Giới hạn context
        )

        raw = self._llm(prompt)
        schema = self._parse_json_response(raw)
        return schema or {}

    # ----------------------------------------------------------------------- #
    #  Step 4: Write schema file                                                #
    # ----------------------------------------------------------------------- #

    def _write_schema(self, schema: Dict[str, Any], analysis_results: List[Dict]) -> None:
        """Ghi university_schema.yaml từ schema dict."""
        # Build intent dict (chuyển từ list sang dict với key = name)
        intents_list = schema.get("intents", [])
        intents_dict = {}
        for intent in intents_list:
            name = intent.pop("name", f"INTENT_{len(intents_dict)}")
            intents_dict[name] = intent

        # Đảm bảo luôn có GENERAL_REGULATION
        if "GENERAL_REGULATION" not in intents_dict:
            intents_dict["GENERAL_REGULATION"] = {
                "description": "Câu hỏi chung, không phụ thuộc ngành/khóa cụ thể",
                "requires_entities": False,
                "required_fields": [],
                "clarification_template": "",
                "examples": ["Quy định chung của trường là gì?"],
            }
            # Đặt GENERAL_REGULATION lên đầu
            intents_dict = {"GENERAL_REGULATION": intents_dict.pop("GENERAL_REGULATION"), **intents_dict}

        # Build domain_entities dict
        entities_list = schema.get("domain_entities", [])
        entities_dict = {}
        for entity in entities_list:
            name = entity.pop("name", f"entity_{len(entities_dict)}")
            entities_dict[name] = entity

        # Build document list từ analysis
        doc_list = [r.get("source_file", "") for r in analysis_results if r.get("source_file")]

        # Compose final schema
        university_name = schema.get("university_name", "University Chatbot")
        output = {
            "university": {
                "name": university_name,
                "generated_at": datetime.now().isoformat(),
                "source_documents": doc_list,
                "total_intents": len(intents_dict),
                "total_entities": len(entities_dict),
            },
            "intents": intents_dict,
            "domain_entities": entities_dict,
        }

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                output,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
            )

    # ----------------------------------------------------------------------- #
    #  Utilities                                                                #
    # ----------------------------------------------------------------------- #

    def _parse_json_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse JSON từ LLM response, thử nhiều chiến lược."""
        import re

        if not raw:
            return None

        # Strategy 1: greedy brace matching
        first = raw.find("{")
        last = raw.rfind("}")
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(raw[first:last + 1])
            except json.JSONDecodeError:
                pass

        # Strategy 2: regex
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(f"[Discovery] Không parse được JSON. Raw (200 chars): {raw[:200]}")
        return None


# ============================================================================
# CLI Entry Point
# ============================================================================

def build_llm_invoker(config: Dict[str, Any]):
    """Khởi tạo LLM invoker từ config."""
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "ollama").lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        import os

        api_key_env = llm_config.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.environ.get(api_key_env) or llm_config.get("api_key", "")
        if not api_key:
            raise ValueError(f"Không tìm thấy Gemini API key (env: {api_key_env})")

        llm = ChatGoogleGenerativeAI(
            model=llm_config.get("model_name", "gemini-2.5-flash"),
            google_api_key=api_key,
            temperature=llm_config.get("temperature", 0.3),
            max_output_tokens=llm_config.get("max_tokens", 2048),
        )

        def invoker(prompt: str) -> str:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            response = llm.invoke(prompt)
            if hasattr(response, "content"):
                return response.content.strip()
            return str(response).strip()

        return invoker

    else:  # ollama
        from langchain_ollama import OllamaLLM

        llm = OllamaLLM(
            model=llm_config.get("model_name", "mistral"),
            base_url=llm_config.get("base_url", "http://localhost:11434"),
            temperature=llm_config.get("temperature", 0.3),
        )

        def invoker(prompt: str) -> str:
            return str(llm.invoke(prompt)).strip()

        return invoker


def main():
    parser = argparse.ArgumentParser(
        description="Auto-discover intent schema từ tài liệu JSON"
    )
    parser.add_argument(
        "--config",
        default="./config.yaml",
        help="Đường dẫn config.yaml (mặc định: ./config.yaml)",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Thư mục chứa JSON (mặc định: lấy từ config)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Đường dẫn output schema (mặc định: lấy từ config)",
    )
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"❌ Config file không tồn tại: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Khởi tạo LLM
    logger.info("🚀 Khởi tạo LLM...")
    llm_invoker = build_llm_invoker(config)

    # Khởi tạo engine
    engine = SchemaDiscoveryEngine(
        config=config,
        llm_invoker=llm_invoker,
        data_dir=Path(args.data_dir) if args.data_dir else None,
        output_path=Path(args.output) if args.output else None,
    )

    # Chạy discovery
    output_path = engine.discover()
    print(f"\n✅ Schema đã được sinh tại: {output_path}")


if __name__ == "__main__":
    main()
