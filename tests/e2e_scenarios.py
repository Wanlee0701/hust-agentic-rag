"""
E2E Test Suite — 10 kịch bản toàn diện cho HUST Agentic RAG Chatbot.

Bao phủ:
  1. Sliding Window Memory (3-turn follow-up)
  2. Intent Gate Clarification (thiếu entity → bổ sung → trả lời)
  3. Từ chối trường khác (Out-of-scope — wrong school)
  4. Từ chối chủ đề không có (Out-of-scope — no data)
  5. Multi-hop retrieval (cần rewrite query mới tìm được)
  6. Học bổng (Scholarship lookup)
  7. Chuẩn ngoại ngữ (Language requirements)
  8. Học phí & tín chỉ (Tuition fee)
  9. Xử lý học vụ (Academic discipline)
  10. Early rejection — từ chối sớm không qua rewrite
"""
import sys
import time
import uuid
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ── Init ──────────────────────────────────────────────────────────
print("=" * 70)
print("E2E TEST SUITE — 10 Scenarios — HUST Agentic RAG Chatbot")
print("=" * 70)

print("\n[INIT] Loading StudentRegulationAgent...")
t0 = time.time()
from src.agent import StudentRegulationAgent
agent = StudentRegulationAgent(config_path="./config.yaml")
print(f"[INIT] Done in {time.time() - t0:.1f}s\n")


def ask(question: str, session_id: str, label: str = "") -> dict:
    print(f"{'─' * 60}")
    if label:
        print(f"  {label}")
    print(f"  USER: {question}")
    t0 = time.time()
    r = agent.answer_question(question, session_id=session_id)
    elapsed = time.time() - t0
    print(f"  BOT  ({elapsed:.1f}s): {r['answer'][:350]}")
    print(f"  conf={r.get('confidence', 0):.0%} | ok={r.get('success')} | "
          f"intent={r.get('intent_name', '?')} | clarify={r.get('needs_clarification')}")
    if r.get('entities'):
        print(f"  entities={r['entities']}")
    if r.get('sources'):
        print(f"  sources={r['sources'][:3]}")
    return r


results = []  # [(name, pass_bool)]


# ======================================================================
# KB 1: ĐA LƯỢT FOLLOW-UP — Sliding Window Memory (3 turns)
# ======================================================================
print("\n" + "=" * 70)
print("KB1: ĐA LƯỢT FOLLOW-UP (Sliding Window Memory)")
print("=" * 70)

sid1 = str(uuid.uuid4())

r = ask("Học bổng KKHT loại xuất sắc được bao nhiêu tiền?",
        sid1, "[Turn 1] Hỏi về KKHT xuất sắc")
time.sleep(0.5)

r = ask("Thế còn loại giỏi thì sao?",
        sid1, "[Turn 2] Follow-up: 'Thế còn loại giỏi thì sao?'")
results.append((
    "KB1.1 Follow-up không trigger clarification",
    not r.get('needs_clarification', True)
))
results.append((
    "KB1.2 Trả lời về KKHT (có 'học bổng' hoặc 'KKHT' hoặc 'loại B')",
    any(w in r.get('answer', '').lower() for w in ['học bổng', 'kkht', 'loại b', 'loại giỏi', '1,2'])
))
time.sleep(0.5)

r = ask("Vậy cần GPA bao nhiêu để được luôn?",
        sid1, "[Turn 3] Follow-up: 'Vậy cần GPA bao nhiêu?'")
results.append((
    "KB1.3 Turn 3 hiểu vẫn đang nói về KKHT (không clarify)",
    not r.get('needs_clarification', True)
))
results.append((
    "KB1.4 Turn 3 trả lời có liên quan đến GPA + học bổng",
    any(w in r.get('answer', '').lower() for w in ['gpa', 'điểm', 'học bổng', 'kkht'])
))


# ======================================================================
# KB 2: CLARIFICATION GATE — Thiếu entity → bổ sung → trả lời
# ======================================================================
print("\n" + "=" * 70)
print("KB2: INTENT GATE CLARIFICATION (Thiếu entity → bổ sung)")
print("=" * 70)

sid2 = str(uuid.uuid4())

r = ask("Học phí ngành của tôi là bao nhiêu?",
        sid2, "[Turn 1] Thiếu cả ngành + khóa")
results.append((
    "KB2.1 Trigger clarification (thiếu ngành + khóa)",
    r.get('needs_clarification', False)
))
results.append((
    "KB2.2 Intent = TUITION_FEE",
    r.get('intent_name') == 'TUITION_FEE'
))

if r.get('needs_clarification'):
    time.sleep(0.5)
    r = ask("Mình học Hệ thống thông tin quản lý khóa K65.",
            sid2, "[Turn 2] Cung cấp đủ: ngành + khóa")
    results.append((
        "KB2.3 Turn 2 không clarify nữa (đã đủ entity)",
        not r.get('needs_clarification', True)
    ))
    results.append((
        "KB2.4 Trả lời về học phí (có 'học phí' hoặc 'tín chỉ' hoặc số tiền)",
        any(w in r.get('answer', '').lower() for w in ['học phí', 'tín chỉ', 'đồng', 'vnđ', 'triệu', 'nghìn'])
    ))


# ======================================================================
# KB 3: TỪ CHỐI TRƯỜNG KHÁC — Out-of-scope (wrong school)
# ======================================================================
print("\n" + "=" * 70)
print("KB3: TỪ CHỐI TRƯỜNG KHÁC (Wrong school)")
print("=" * 70)

r = ask("Quy chế thi lại của trường Đại học Kinh tế Quốc dân quy định thế nào?",
        str(uuid.uuid4()), "[Case] Hỏi về NEU")
results.append((
    "KB3.1 Confidence < 35% hoặc success=False",
    r.get('confidence', 0) < 0.35 or not r.get('success')
))
results.append((
    "KB3.2 Từ chối rõ ràng (có 'không tìm thấy' hoặc 'xin lỗi' hoặc 'liên hệ')",
    any(w in r.get('answer', '').lower() for w in ['không tìm thấy', 'không có thông tin', 'xin lỗi', 'liên hệ'])
))


# ======================================================================
# KB 4: TỪ CHỐI CHỦ ĐỀ KHÔNG CÓ — Out-of-scope (no data)
# ======================================================================
print("\n" + "=" * 70)
print("KB4: TỪ CHỐI CHỦ ĐỀ KHÔNG CÓ (No data in KB)")
print("=" * 70)

r = ask("Nhà vệ sinh tòa nhà D7 ở tầng mấy?",
        str(uuid.uuid4()), "[Case] Hỏi về cơ sở vật chất")
results.append((
    "KB4.1 Từ chối / confidence thấp (không có trong quy chế)",
    r.get('confidence', 0) < 0.50 or not r.get('success') or
    any(w in r.get('answer', '').lower() for w in ['không tìm thấy', 'không có thông tin', 'xin lỗi'])
))


# ======================================================================
# KB 5: MULTI-HOP RETRIEVAL — Câu hỏi cần diễn đạt lại
# ======================================================================
print("\n" + "=" * 70)
print("KB5: MULTI-HOP RETRIEVAL (Cần rewrite query)")
print("=" * 70)

r = ask("Bị trượt 14 tín thì làm sao?",
        str(uuid.uuid4()), "[Case] Ngôn ngữ sinh viên → cần map sang thuật ngữ quy chế")
results.append((
    "KB5.1 Trả lời về cảnh cáo học vụ / buộc thôi học",
    any(w in r.get('answer', '').lower() for w in ['cảnh cáo', 'cảnh báo', 'buộc thôi học', 'tín chỉ'])
))
results.append((
    "KB5.2 Có confidence > 35% (tìm được tài liệu liên quan)",
    r.get('confidence', 0) > 0.35
))


# ======================================================================
# KB 6: HỌC BỔNG TDN — Scholarship lookup
# ======================================================================
print("\n" + "=" * 70)
print("KB6: HỌC BỔNG TRẦN ĐẠI NGHĨA")
print("=" * 70)

r = ask("Điều kiện nhận học bổng Trần Đại Nghĩa là gì?",
        str(uuid.uuid4()), "[Case] Tra cứu học bổng TDN")
results.append((
    "KB6.1 Intent = SCHOLARSHIP",
    r.get('intent_name') == 'SCHOLARSHIP'
))
results.append((
    "KB6.2 Trả lời có nội dung về học bổng TDN",
    any(w in r.get('answer', '').lower() for w in ['trần đại nghĩa', 'tdn', 'điều kiện', 'gpa', 'học lực'])
))


# ======================================================================
# KB 7: CHUẨN NGOẠI NGỮ — Language requirements
# ======================================================================
print("\n" + "=" * 70)
print("KB7: CHUẨN NGOẠI NGỮ")
print("=" * 70)

r = ask("Sinh viên K68 cần TOEIC bao nhiêu để tốt nghiệp?",
        str(uuid.uuid4()), "[Case] Tra cứu ngoại ngữ K68")
results.append((
    "KB7.1 Intent = LANGUAGE_REQUIREMENT",
    r.get('intent_name') == 'LANGUAGE_REQUIREMENT'
))
results.append((
    "KB7.2 Trả lời có đề cập đến ngoại ngữ / TOEIC / chuẩn đầu ra",
    any(w in r.get('answer', '').lower() for w in ['toeic', 'ngoại ngữ', 'tiếng anh', 'chuẩn', 'ielts'])
))


# ======================================================================
# KB 8: XỬ LÝ HỌC VỤ — Academic discipline
# ======================================================================
print("\n" + "=" * 70)
print("KB8: XỬ LÝ HỌC VỤ (Academic discipline)")
print("=" * 70)

r = ask("GPA dưới bao nhiêu thì bị cảnh cáo học vụ?",
        str(uuid.uuid4()), "[Case] Hỏi về ngưỡng cảnh cáo")
results.append((
    "KB8.1 Trả lời có số liệu về GPA hoặc mức cảnh cáo",
    any(w in r.get('answer', '').lower() for w in ['gpa', 'cảnh cáo', 'cảnh báo', 'điểm', '1.', '2.'])
))

r = ask("Sinh viên bị buộc thôi học khi nào?",
        str(uuid.uuid4()), "[Case] Hỏi về buộc thôi học")
results.append((
    "KB8.2 Trả lời về điều kiện buộc thôi học",
    any(w in r.get('answer', '').lower() for w in ['buộc thôi học', 'tín chỉ', 'gpa', 'cảnh cáo', 'nợ'])
))


# ======================================================================
# KB 9: CÂU HỎI NGẮN / MƠ HỒ — Edge cases
# ======================================================================
print("\n" + "=" * 70)
print("KB9: EDGE CASES (Câu hỏi ngắn / mơ hồ)")
print("=" * 70)

r = ask("Học lại được không?",
        str(uuid.uuid4()), "[Case A] Câu hỏi rất ngắn, mơ hồ")
results.append((
    "KB9.1 Vẫn trả lời được (có nội dung về học lại/thi lại)",
    len(r.get('answer', '')) > 30 and
    any(w in r.get('answer', '').lower() for w in ['học lại', 'thi lại', 'đăng ký', 'học phần', 'tín chỉ'])
))

r = ask("Bảo lưu kết quả cần những gì?",
        str(uuid.uuid4()), "[Case B] Câu hỏi về thủ tục bảo lưu")
results.append((
    "KB9.2 Trả lời được về bảo lưu hoặc từ chối có lý do",
    len(r.get('answer', '')) > 30
))


# ======================================================================
# KB 10: EARLY REJECTION — Từ chối sớm không qua rewrite
# ======================================================================
print("\n" + "=" * 70)
print("KB10: EARLY REJECTION (Ngắt luồng sớm khi 0 docs)")
print("=" * 70)

r = ask("Cách nấu phở bò Hà Nội ngon?",
        str(uuid.uuid4()), "[Case] Hoàn toàn không liên quan đến quy chế")

# Kiểm tra không tốn rewrite LLM call: answer phải là template từ chối
is_template = any(w in r.get('answer', '').lower()
                  for w in ['không tìm thấy', 'không có thông tin', 'xin lỗi'])
results.append((
    "KB10.1 Từ chối (template, không hallucinate)",
    is_template
))
results.append((
    "KB10.2 Confidence thấp (≤ 35%)",
    r.get('confidence', 0) <= 0.35 or not r.get('success')
))


# ======================================================================
# TỔNG KẾT
# ======================================================================
print("\n\n" + "=" * 70)
print("TỔNG KẾT")
print("=" * 70)

passed = sum(1 for _, ok in results if ok)
total = len(results)
for name, ok in results:
    print(f"  {'✅' if ok else '❌'}  {name}")

print(f"\n  {passed}/{total} tests passed ({passed/total*100:.0f}%)")

# Phân loại theo kịch bản
print(f"\n  Theo kịch bản:")
scenarios = {
    "KB1  Follow-up Memory":     [r for n, r in results if n.startswith("KB1")],
    "KB2  Clarification Gate":   [r for n, r in results if n.startswith("KB2")],
    "KB3  Wrong School":         [r for n, r in results if n.startswith("KB3")],
    "KB4  No Data":              [r for n, r in results if n.startswith("KB4")],
    "KB5  Multi-hop":            [r for n, r in results if n.startswith("KB5")],
    "KB6  Scholarship TDN":      [r for n, r in results if n.startswith("KB6")],
    "KB7  Language Req":         [r for n, r in results if n.startswith("KB7")],
    "KB8  Academic Discipline":  [r for n, r in results if n.startswith("KB8")],
    "KB9  Edge Cases":           [r for n, r in results if n.startswith("KB9")],
    "KB10 Early Rejection":      [r for n, r in results if n.startswith("KB10")],
}
for name, res in scenarios.items():
    ok = sum(res)
    total_sc = len(res)
    bar = "█" * ok + "░" * (total_sc - ok)
    print(f"  {name:<22} {bar}  {ok}/{total_sc}")

print("=" * 70)
