"""
Prompts - Các prompt templates cho Agent ReACT
Cải thiện: thêm context HUST, yêu cầu trích dẫn cụ thể, xử lý không tìm thấy
"""

# ------------------------------------------------------------------ #
# System Prompt — Ngữ cảnh & vai trò của Agent                       #
# ------------------------------------------------------------------ #
REACT_SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên về quy định và chính sách đào tạo tại Đại học Bách khoa Hà Nội (HUST/ĐHBK Hà Nội).

Nhiệm vụ: Trả lời chính xác các câu hỏi của sinh viên dựa trên các tài liệu quy chế chính thức.

Tài liệu bạn có quyền truy cập:
- Quy chế đào tạo (Quy_che_25.pdf)
- Quy chế công tác sinh viên (Quy_che_CTSV)
- Học bổng Trần Đại Nghĩa, Học bổng KKHT
- Quyết định ngoại ngữ K65, K68, K70
- Hướng dẫn chuyển tiếp kỹ sư 180TC
- Quyết định chuyển đổi học phần tương đương

Nguyên tắc:
1. Chỉ dùng thông tin từ tài liệu được cung cấp, KHÔNG bịa đặt
2. Trích dẫn rõ ràng: số Điều, Chương, tên văn bản
3. Nếu thông tin không đủ → thừa nhận giới hạn, gợi ý liên hệ phòng ban
4. Trả lời bằng tiếng Việt, rõ ràng, có cấu trúc"""

# ------------------------------------------------------------------ #
# ReACT Format Prompt                                                  #
# ------------------------------------------------------------------ #
REACT_FORMAT_PROMPT = """Quy trình suy luận ReACT:

Question: [câu hỏi cần trả lời]
Thought: [phân tích câu hỏi, xác định thông tin cần tìm]
Action: [Retrieve | Refine | Verify | Answer]
Action Input: [nội dung cụ thể cho action]
Observation: [kết quả nhận được]
... (lặp lại tối đa 5 lần)
Thought: Tôi đã đủ thông tin để trả lời
Final Answer: [câu trả lời đầy đủ, có trích dẫn nguồn cụ thể]

Lưu ý:
- Confidence < 0.75 → tiếp tục tìm kiếm
- Confidence ≥ 0.75 hoặc đã 5 lần → đưa ra Final Answer
- Luôn trích dẫn: "Theo Điều X, Chương Y của [tên văn bản]..." """

# ------------------------------------------------------------------ #
# Main ReACT Prompt                                                    #
# ------------------------------------------------------------------ #
REACT_MAIN_PROMPT = f"""{REACT_SYSTEM_PROMPT}

{REACT_FORMAT_PROMPT}

---
Question: {{question}}
Thought:"""

# ------------------------------------------------------------------ #
# Verification Prompt                                                  #
# ------------------------------------------------------------------ #
VERIFICATION_PROMPT = """Đánh giá chất lượng câu trả lời sau:

Câu trả lời: "{answer}"

Tiêu chí đánh giá:
1. Rõ ràng (clarity): Dễ hiểu, không mơ hồ?
2. Cụ thể (specificity): Có số liệu, điều khoản cụ thể?
3. Trung thực (honesty): Thừa nhận giới hạn nếu không đủ thông tin?
4. Đầy đủ (completeness): Trả lời hết câu hỏi chưa?

Trả về JSON:
{{
    "sufficient": true/false,
    "confidence": 0.0-1.0,
    "reason": "Lý do ngắn gọn"
}}"""

# ------------------------------------------------------------------ #
# Query Refinement Prompt                                              #
# ------------------------------------------------------------------ #
QUERY_REFINEMENT_PROMPT = """Bạn là chuyên gia về quy chế đào tạo ĐHBK Hà Nội.

Câu hỏi gốc: "{original_query}"

Tạo 3 cách diễn đạt khác nhau, dùng thuật ngữ/từ khóa khác nhau để tìm kiếm trong văn bản quy chế:

Ví dụ:
Câu gốc: "Học lại được không?"
→ 1. "Quy định về đăng ký học lại học phần chưa đạt"
→ 2. "Điều kiện và thủ tục học lại môn có điểm F"
→ 3. "Số lần thi lại và học lại tối đa theo quy chế đào tạo"

Tạo 3 cách cho: "{original_query}"
1. 
2. 
3. """

# ------------------------------------------------------------------ #
# Confidence Scoring Prompt                                            #
# ------------------------------------------------------------------ #
CONFIDENCE_SCORING_PROMPT = """Ước tính độ tin cậy của câu trả lời:

Câu hỏi: "{question}"
Câu trả lời: "{answer}"
Số tài liệu tìm được: {retrieval_count}
Điểm tương đồng trung bình: {avg_similarity:.2f}

Trả về JSON:
{{
    "confidence": 0.0-1.0,
    "explanation": "Lý do ngắn gọn"
}}"""

# ------------------------------------------------------------------ #
# Error Handling Prompt                                                #
# ------------------------------------------------------------------ #
ERROR_HANDLING_PROMPT = """Không tìm thấy thông tin cho câu hỏi: "{query}"

Hướng dẫn người dùng:
1. Xác nhận không có thông tin trong CSDL hiện tại
2. Gợi ý cách hỏi lại
3. Chỉ dẫn liên hệ phòng ban phù hợp

Gợi ý:
- Phòng Đào tạo: phụ trách học phí, học bổng, kế hoạch học tập
- Phòng CTSV: kỷ luật, khen thưởng, hoạt động SV
- Website: https://hust.edu.vn"""

# ------------------------------------------------------------------ #
# Dictionary tổng hợp                                                  #
# ------------------------------------------------------------------ #
PROMPTS = {
    "system": REACT_SYSTEM_PROMPT,
    "format": REACT_FORMAT_PROMPT,
    "main": REACT_MAIN_PROMPT,
    "verification": VERIFICATION_PROMPT,
    "query_refinement": QUERY_REFINEMENT_PROMPT,
    "confidence_scoring": CONFIDENCE_SCORING_PROMPT,
    "error_handling": ERROR_HANDLING_PROMPT,
}


def get_prompt(prompt_name: str, **kwargs) -> str:
    """Lấy prompt template và substitute variables"""
    if prompt_name not in PROMPTS:
        raise ValueError(f"Unknown prompt: {prompt_name}. Available: {list(PROMPTS.keys())}")
    try:
        return PROMPTS[prompt_name].format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing variable in prompt '{prompt_name}': {e}")


def get_react_prompt(question: str) -> str:
    """Lấy ReACT prompt chính cho một câu hỏi"""
    return get_prompt("main", question=question)


# ------------------------------------------------------------------ #
# [v5 — Auto-Discovery] Dynamic System Prompt Builder                 #
# ------------------------------------------------------------------ #

def build_system_prompt(
    university_name: str = "",
    document_list: list = None,
) -> str:
    """
    Sinh REACT_SYSTEM_PROMPT động dựa trên thông tin từ university_schema.yaml.

    Nếu university_name và document_list được cung cấp → tạo prompt cá nhân hóa.
    Nếu không → trả về REACT_SYSTEM_PROMPT mặc định (không thay đổi hành vi cũ).

    Args:
        university_name: Tên trường đại học (từ university_schema.yaml['university']['name']).
        document_list: Danh sách tài liệu (từ university_schema.yaml['university']['source_documents']).

    Returns:
        System prompt string đã được inject thông tin trường.
    """
    document_list = document_list or []

    if not university_name and not document_list:
        return REACT_SYSTEM_PROMPT

    # Build tên trường (fallback nếu trống)
    uni_display = university_name if university_name else "trường đại học"

    # Build danh sách tài liệu
    if document_list:
        # Bỏ phần mở rộng .json để hiển thị sạch hơn
        doc_names = [
            d.replace(".json", "").replace("_", " ")
            for d in document_list
        ]
        doc_lines = "\n".join(f"- {name}" for name in doc_names[:15])  # Giới hạn 15 tài liệu
    else:
        doc_lines = "- (Tài liệu quy chế của trường)"

    return f"""Bạn là trợ lý AI chuyên về quy định và chính sách đào tạo tại {uni_display}.

Nhiệm vụ: Trả lời chính xác các câu hỏi của sinh viên dựa trên các tài liệu quy chế chính thức.

Tài liệu bạn có quyền truy cập:
{doc_lines}

Nguyên tắc:
1. Chỉ dùng thông tin từ tài liệu được cung cấp, KHÔNG bịa đặt
2. Trích dẫn rõ ràng: số Điều, Chương, tên văn bản
3. Nếu thông tin không đủ → thừa nhận giới hạn, gợi ý liên hệ phòng ban
4. Trả lời bằng ngôn ngữ của câu hỏi, rõ ràng, có cấu trúc"""
