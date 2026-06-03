"""
Phase 2 — Test Agent End-to-End với câu hỏi thực tế về quy chế HUST
Chạy: python tests/test_agent_flow.py
"""
import sys
import io
import time
import logging
from pathlib import Path

# Fix encoding Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.WARNING)  # Tắt noise

# ------------------------------------------------------------------ #
# Bộ câu hỏi kiểm thử thực tế                                        #
# ------------------------------------------------------------------ #
# Mỗi entry: (câu hỏi, từ khóa kỳ vọng trong câu trả lời, ghi chú)
TEST_CASES = [
    (
        "Bao nhiêu tín chỉ thì tốt nghiệp cử nhân?",
        ["132", "tín chỉ"],
        "Quy chế đào tạo - Điều 2",
    ),
    (
        "Điểm thi dưới bao nhiêu thì bị coi là điểm liệt?",
        ["3", "liệt", "điểm"],
        "Quy chế đào tạo - Điều 5",
    ),
    (
        "GPA bao nhiêu thì bị cảnh báo học vụ?",
        ["2", "cảnh báo", "GPA"],
        "Quy chế đào tạo - học vụ",
    ),
    (
        "Sinh viên có thể học lại học phần đã đạt không?",
        ["học lại", "cải thiện", "điểm"],
        "Quy chế đào tạo - Điều 5 khoản 8",
    ),
    (
        "Điều kiện và tiêu chuẩn học bổng Trần Đại Nghĩa là gì?",
        ["học bổng", "Trần Đại Nghĩa"],
        "Hoc_bong_TDN_2023.pdf",
    ),
    (
        "Chuẩn ngoại ngữ tiếng Anh của sinh viên K68 là gì?",
        ["K68", "ngoại ngữ", "IELTS"],
        "QD_NN_K68.pdf",
    ),
    (
        "Nếu không nộp học phí đúng hạn thì bị xử lý như thế nào?",
        ["học phí", "đình chỉ"],
        "Quy chế đào tạo - Điều 9",
    ),
    (
        "Sinh viên có được hoãn thi cuối kỳ không? Điều kiện là gì?",
        ["hoãn thi", "ốm", "lý do"],
        "Quy chế đào tạo - Điều 6",
    ),
]

# ------------------------------------------------------------------ #
# Khởi tạo Agent                                                      #
# ------------------------------------------------------------------ #
print("\n" + "=" * 65)
print("  AGENT END-TO-END TEST — AgenticRAG @ HUST")
print("=" * 65)
print("\n⏳ Khởi tạo Agent (load embedding model + connect Chroma DB)...")

try:
    from src.agent import StudentRegulationAgent

    t0 = time.time()
    agent = StudentRegulationAgent(config_path="./config.yaml")
    init_time = time.time() - t0
    print(f"✅ Agent sẵn sàng (khởi tạo mất {init_time:.1f}s)\n")
except Exception as e:
    print(f"❌ Không thể khởi tạo Agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ------------------------------------------------------------------ #
# Chạy từng test case                                                  #
# ------------------------------------------------------------------ #
all_results = []

for i, (question, expected_keywords, note) in enumerate(TEST_CASES, 1):
    print(f"\n{'─'*65}")
    print(f"[{i}/{len(TEST_CASES)}] {question}")
    print(f"         (Kỳ vọng từ khóa: {expected_keywords})")
    print()

    t_start = time.time()
    result = agent.answer_question(question)
    elapsed = time.time() - t_start

    success = result.get("success", False)
    confidence = result.get("confidence", 0.0)
    answer = result.get("answer", "")
    state = result.get("state")
    sources = state.sources if state else []

    # Kiểm tra từ khóa kỳ vọng
    answer_lower = answer.lower()
    kw_hits = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    kw_score = len(kw_hits) / len(expected_keywords) if expected_keywords else 0

    # Đánh giá
    if success and confidence >= 0.6 and kw_score >= 0.5:
        status = "✅ PASS"
    elif success and confidence >= 0.3:
        status = "⚠️  PARTIAL"
    else:
        status = "❌ FAIL"

    print(f"  Trạng thái  : {status}")
    print(f"  Thời gian   : {elapsed:.1f}s")
    print(f"  Confidence  : {confidence:.0%}")
    print(f"  Từ khóa hit : {kw_hits} ({kw_score:.0%})")
    print(f"  Sources     : {sources if sources else '(không có)'}")
    print(f"\n  💬 Câu trả lời:")
    # In từng dòng, indent
    for line in answer[:600].split("\n"):
        print(f"     {line}")
    if len(answer) > 600:
        print("     ... [cắt bớt]")

    if state and state.steps:
        print(f"\n  🔍 Reasoning steps ({len(state.steps)}):")
        for step in state.steps:
            print(f"     [{step.iteration}] {step.action}: {step.action_input[:60]}")

    all_results.append({
        "question": question,
        "status": status,
        "confidence": confidence,
        "kw_score": kw_score,
        "elapsed": elapsed,
        "success": success,
        "sources": sources,
        "note": note,
    })


# ------------------------------------------------------------------ #
# Summary                                                             #
# ------------------------------------------------------------------ #
print(f"\n\n{'='*65}")
print("  TỔNG KẾT")
print(f"{'='*65}")

passed = sum(1 for r in all_results if r["status"] == "✅ PASS")
partial = sum(1 for r in all_results if r["status"] == "⚠️  PARTIAL")
failed = sum(1 for r in all_results if r["status"] == "❌ FAIL")
avg_conf = sum(r["confidence"] for r in all_results) / len(all_results)
avg_time = sum(r["elapsed"] for r in all_results) / len(all_results)

print(f"\n  ✅ PASS    : {passed}/{len(all_results)}")
print(f"  ⚠️  PARTIAL : {partial}/{len(all_results)}")
print(f"  ❌ FAIL    : {failed}/{len(all_results)}")
print(f"\n  📊 Avg Confidence : {avg_conf:.0%}")
print(f"  ⏱️  Avg Time/query : {avg_time:.1f}s")
print()

# Chi tiết từng kết quả
print(f"  {'#':<3} {'Status':<12} {'Conf':<8} {'KW%':<8} {'Time':<8} Câu hỏi")
print(f"  {'─'*60}")
for i, r in enumerate(all_results, 1):
    q_short = r["question"][:35] + "..." if len(r["question"]) > 35 else r["question"]
    print(f"  {i:<3} {r['status']:<12} {r['confidence']:.0%}{'':>4} "
          f"{r['kw_score']:.0%}{'':>4} {r['elapsed']:.1f}s{'':>3} {q_short}")

print()
if passed == len(all_results):
    print("  🎉 Tất cả test cases PASS! Agent hoạt động tốt.")
elif passed + partial >= len(all_results) * 0.7:
    print("  👍 Hơn 70% test cases đạt. Agent đủ điều kiện tích hợp UI.")
else:
    print("  ⚠️  Dưới 70% test cases đạt. Cần kiểm tra lại pipeline.")
print()
