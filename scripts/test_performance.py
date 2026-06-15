#!/usr/bin/env python
"""
Performance Test Script - Test performance của agent
Chạy: python scripts/test_performance.py "Câu hỏi test"
"""
import sys
import logging
import time
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def print_separator(title=""):
    """Print formatted separator"""
    width = 80
    if title:
        print(f"\n{'='*width}")
        print(f"  {title}")
        print(f"{'='*width}")
    else:
        print(f"\n{'='*width}\n")


def test_performance(questions: list):
    """Test performance cho multiple questions"""
    
    print_separator("🚀 HUST AgenticRAG - Performance Test Suite")
    
    # Import agent
    logger.info("📥 Loading StudentRegulationAgent...")
    from src.agent.orchestrator import StudentRegulationAgent
    
    try:
        agent = StudentRegulationAgent(config_path="./config.yaml")
        logger.info("✅ Agent loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load agent: {e}")
        return
    
    # Store results
    results = []
    
    for i, question in enumerate(questions, 1):
        print_separator(f"Test {i}/{len(questions)}: {question[:60]}")
        
        start_total = time.time()
        
        try:
            # Call agent
            response = agent.answer_question(question)
            
            total_time = (time.time() - start_total) * 1000
            
            # Extract performance data
            perf_data = response.get("performance", {})
            breakdown = perf_data.get("breakdown", {})
            slowest = perf_data.get("slowest_steps", [])
            
            # Print results
            print(f"\n✅ Status: {response.get('success')}")
            print(f"⏱️  Total Time: {total_time:.0f}ms ({total_time/1000:.1f}s)")
            print(f"🎯 Confidence: {response.get('confidence'):.1%}")
            print(f"📝 Answer Length: {len(response.get('answer', ''))} chars")
            
            # Breakdown
            if breakdown:
                print("\n📊 Time Breakdown:")
                for step, dur in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                    pct = (dur / total_time * 100) if total_time > 0 else 0
                    print(f"  {step:<40} {dur:>7.0f}ms ({pct:>5.1f}%)")
            
            # Slowest steps
            if slowest:
                print("\n🐢 Top 5 Slowest Steps:")
                for step, dur in slowest[:5]:
                    print(f"  • {step}: {dur:.0f}ms")
            
            # Store result
            results.append({
                "question": question,
                "total_time_ms": total_time,
                "confidence": response.get("confidence"),
                "success": response.get("success"),
                "answer_length": len(response.get("answer", "")),
                "breakdown": breakdown,
            })
            
            # Check for slow response
            if total_time > 5000:
                logger.warning(f"⚠️  SLOW RESPONSE ({total_time:.0f}ms > 5000ms)")
            elif total_time > 3000:
                logger.warning(f"⚠️  MODERATE LATENCY ({total_time:.0f}ms)")
            else:
                logger.info(f"✅ Good response time: {total_time:.0f}ms")
        
        except Exception as e:
            logger.error(f"❌ Error processing question: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "question": question,
                "error": str(e),
            })
    
    # Summary
    print_separator("📊 SUMMARY")
    
    if results:
        successful = [r for r in results if "error" not in r]
        
        if successful:
            total_times = [r["total_time_ms"] for r in successful]
            avg_time = sum(total_times) / len(total_times)
            max_time = max(total_times)
            min_time = min(total_times)
            
            print(f"\n✅ Successful: {len(successful)}/{len(results)}")
            print(f"⏱️  Average Time: {avg_time:.0f}ms")
            print(f"📈 Max Time: {max_time:.0f}ms")
            print(f"📉 Min Time: {min_time:.0f}ms")
            
            # Confidence stats
            confidences = [r["confidence"] for r in successful if r["confidence"] is not None]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                print(f"🎯 Average Confidence: {avg_conf:.1%}")
        
        if len(results) > len(successful):
            failed = len(results) - len(successful)
            print(f"\n❌ Failed: {failed}/{len(results)}")
    
    # Save results
    output_file = Path("logs") / f"perf_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📁 Results saved to: {output_file}")
    
    print_separator("✅ Test Complete")


def main():
    """Main entry point"""
    
    # Sample test questions
    default_questions = [
        "Có được học lại môn học không?",
        "Quy chế tính điểm học phần như thế nào?",
        "Học sinh có được hưởng học bổng không?",
    ]
    
    # Check command line args
    if len(sys.argv) > 1:
        questions = sys.argv[1:]
        print(f"Testing with {len(questions)} custom question(s)...")
    else:
        questions = default_questions
        print(f"Using default test questions...")
    
    test_performance(questions)


if __name__ == "__main__":
    main()
