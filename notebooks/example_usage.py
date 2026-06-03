"""
Example Usage - Ví dụ cách sử dụng Agent
"""
import logging
from src.agent import StudentRegulationAgent

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_1_simple_question():
    """Ví dụ 1: Trả lời một câu hỏi đơn giản"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Simple Question")
    print("="*60)
    
    # Khởi tạo agent
    agent = StudentRegulationAgent(config_path="./config.yaml")
    
    # Đặt câu hỏi
    question = "Học phí năm nhất bao nhiêu?"
    print(f"\n❓ Câu hỏi: {question}")
    
    # Nhận câu trả lời
    result = agent.answer_question(question)
    
    # In kết quả
    print(f"\n✅ Câu trả lời: {result['answer']}")
    print(f"📊 Độ tin cậy: {result['confidence']:.0%}")
    print(f"✓ Thành công: {result['success']}")
    
    # In chi tiết state
    if result['state']:
        print(f"\n📈 Chi tiết quá trình reasoning:")
        print(f"   - Iterations: {result['state'].iterations}")
        print(f"   - Sources: {result['state'].sources}")


def example_2_complex_question():
    """Ví dụ 2: Trả lời câu hỏi phức tạp"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Complex Question")
    print("="*60)
    
    agent = StudentRegulationAgent()
    
    question = "Nếu GPA dưới 2.0, tôi còn được tiếp tục học không? Có những lựa chọn nào?"
    print(f"\n❓ Câu hỏi: {question}")
    
    result = agent.answer_question(question)
    
    print(f"\n✅ Câu trả lời:\n{result['answer']}")
    print(f"\n📊 Độ tin cậy: {result['confidence']:.0%}")
    
    # In toàn bộ state summary
    if result['state']:
        result['state'].print_summary()


def example_3_batch_questions():
    """Ví dụ 3: Trả lời nhiều câu hỏi"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Batch Questions")
    print("="*60)
    
    agent = StudentRegulationAgent()
    
    questions = [
        "Có được học lại không?",
        "Học bổng là gì?",
        "Quy định về điểm danh là gì?",
    ]
    
    print(f"\n📝 Sẽ trả lời {len(questions)} câu hỏi...")
    
    results = agent.batch_answer_questions(questions)
    
    # In tóm tắt
    print("\n📊 TÓNG TẮT KẾT QUẢ:")
    print("-" * 60)
    for i, (q, result) in enumerate(zip(questions, results), 1):
        print(f"\n[Câu {i}] {q}")
        print(f"  Trả lời: {result['answer'][:100]}...")
        print(f"  Confidence: {result['confidence']:.0%}")
        print(f"  Success: {result['success']}")


def example_4_with_state_tracking():
    """Ví dụ 4: Tracking state chi tiết"""
    print("\n" + "="*60)
    print("EXAMPLE 4: State Tracking")
    print("="*60)
    
    agent = StudentRegulationAgent()
    
    question = "Quy định về học phí là gì?"
    print(f"\n❓ Câu hỏi: {question}")
    
    result = agent.answer_question(question)
    state = result['state']
    
    # Chi tiết từng iteration
    print(f"\n📈 Chi tiết các iteration:")
    print(f"Total iterations: {state.iterations}/{state.max_iterations}")
    
    for i, step in enumerate(state.steps, 1):
        print(f"\n  [Iteration {i}]")
        print(f"    💭 Thought: {step.thought}")
        print(f"    🔧 Action: {step.action}")
        print(f"    📥 Input: {step.action_input}")
        print(f"    👀 Observation: {step.observation[:100]}...")
    
    # Final answer
    print(f"\n✅ FINAL ANSWER:")
    print(f"   {state.answer}")
    print(f"\n📊 Confidence breakdown:")
    print(f"   Score: {state.confidence:.2%}")
    print(f"   Sources: {len(state.sources)} documents")
    print(f"   Iterations: {state.iterations} steps")


def example_5_error_handling():
    """Ví dụ 5: Xử lý lỗi"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Error Handling")
    print("="*60)
    
    agent = StudentRegulationAgent()
    
    # Câu hỏi không liên quan
    question = "1 + 1 = bao nhiêu?"  # Không liên quan đến quy định
    print(f"\n❓ Câu hỏi (không liên quan): {question}")
    
    try:
        result = agent.answer_question(question)
        
        print(f"\n❌ Kết quả: {result['answer']}")
        print(f"📊 Confidence: {result['confidence']:.0%}")
        print(f"✓ Success: {result['success']}")
        
        if result['state'] and result['state'].error:
            print(f"⚠️ Error: {result['state'].error}")
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        logger.error(f"Error in example_5: {str(e)}")


def main():
    """Main function - chạy tất cả examples"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           AGENT USAGE EXAMPLES - STUDENT REGULATION        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    try:
        # Chạy các ví dụ
        example_1_simple_question()
        example_2_complex_question()
        example_3_batch_questions()
        example_4_with_state_tracking()
        example_5_error_handling()
        
        print("\n" + "="*60)
        print("✅ All examples completed successfully!")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        logger.error(f"Error in main: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
