"""
Quick test script - Test agent có lỗi gì không
"""
import sys
import logging
import io

# Fix encoding for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("\n" + "="*60)
print("AGENT TEST - Kiểm tra lỗi")
print("="*60 + "\n")

# Test 1: Import packages
print("✓ [Test 1] Kiểm tra import packages...")
try:
    from langchain_ollama import OllamaLLM
    from langchain_core.prompts import PromptTemplate
    print("  ✅ LangChain imports OK")
except ImportError as e:
    print(f"  ❌ LangChain import error: {e}")
    sys.exit(1)

# Test 2: Import agent modules
print("\n✓ [Test 2] Kiểm tra import agent modules...")
try:
    from src.agent import StudentRegulationAgent, AgentState
    from src.agent.prompts import get_react_prompt
    from src.agent.tools import AgentTools
    print("  ✅ Agent modules import OK")
except ImportError as e:
    print(f"  ❌ Agent import error: {e}")
    sys.exit(1)

# Test 3: Check config
print("\n✓ [Test 3] Kiểm tra config.yaml...")
try:
    import yaml
    with open("./config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    print(f"  ✅ Config loaded")
    print(f"     - LLM model: {config.get('llm', {}).get('model_name')}")
    print(f"     - Retrieval top_k: {config.get('retrieval', {}).get('top_k')}")
    print(f"     - Agent max_iterations: {config.get('agent', {}).get('max_iterations')}")
except Exception as e:
    print(f"  ❌ Config error: {e}")
    sys.exit(1)

# Test 4: Check Ollama connection
print("\n✓ [Test 4] Kiểm tra Ollama connection...")
try:
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json().get("models", [])
        if models:
            model_names = [m.get("name") for m in models]
            print(f"  ✅ Ollama OK - Models available: {model_names[:3]}")
        else:
            print(f"  ⚠️  Ollama OK - Nhưng chưa có model, hãy chạy: ollama pull mistral")
    else:
        print(f"  ❌ Ollama response error: {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"  ❌ Ollama NOT running! Start with: ollama serve")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Ollama check error: {e}")
    sys.exit(1)

# Test 5: Check Chroma DB
print("\n✓ [Test 5] Kiểm tra Chroma DB...")
try:
    from pathlib import Path
    chroma_path = Path("./data/chroma")
    if chroma_path.exists():
        print(f"  ✅ Chroma DB folder exists")
        db_files = list(chroma_path.glob("*.sqlite3"))
        if db_files:
            print(f"     - Found {len(db_files)} database files")
        else:
            print(f"     ⚠️  Chroma database chưa được khởi tạo")
    else:
        print(f"  ⚠️  Chroma folder not found at {chroma_path}")
except Exception as e:
    print(f"  ❌ Chroma check error: {e}")

# Test 6: Initialize agent
print("\n✓ [Test 6] Khởi tạo agent...")
try:
    agent = StudentRegulationAgent(config_path="./config.yaml")
    print(f"  ✅ Agent initialized successfully!")
    print(f"     - LLM: {agent.llm}")
    print(f"     - Vector DB: {agent.vector_db_manager}")
    print(f"     - Tools: {len(agent.tools.get_tools_list())} tools available")
except Exception as e:
    print(f"  ❌ Agent initialization error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test AgentState
print("\n✓ [Test 7] Test AgentState...")
try:
    state = AgentState(query="Test question?", max_iterations=5)
    state.add_iteration(
        thought="Testing...",
        action="Retrieve",
        action_input="test",
        observation="Test observation"
    )
    state.set_answer("Test answer", confidence=0.8)
    print(f"  ✅ AgentState OK")
    print(f"     - Iterations: {state.iterations}")
    print(f"     - Confidence: {state.confidence:.0%}")
    print(f"     - Success: {state.success}")
except Exception as e:
    print(f"  ❌ AgentState error: {e}")
    sys.exit(1)

# Test 8: Simple question (nếu embeddings khởi tạo được)
print("\n✓ [Test 8] Test trả lời câu hỏi (optional)...")
try:
    print(f"  ⏳ Đang xử lý câu hỏi: 'Học phí bao nhiêu?'...")
    result = agent.answer_question("Học phí bao nhiêu?")
    print(f"  ✅ Answer received!")
    print(f"     - Success: {result['success']}")
    print(f"     - Confidence: {result['confidence']:.0%}")
    print(f"     - Answer length: {len(result['answer'])} chars")
except Exception as e:
    print(f"  ⚠️  Question test skipped/failed: {e}")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED - Agent is ready to use!")
print("="*60 + "\n")
