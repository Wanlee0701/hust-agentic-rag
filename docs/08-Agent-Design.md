# 08. Agent Design - Reasoning Loop & Tool Integration

## 📚 Mục Tiêu
Hiểu **chi tiết cách Agent hoạt động** - reasoning loop, how to make decisions, tool usage, và implementation của ReACT pattern.

---

## 1. Agent Role in System

### 1.1 What Does Agent Do?

```
               User Query
                   │
                   ▼
    ┌──────────────────────────────┐
    │   AGENT (LLM-powered)        │
    │                              │
    │  "Tôi cần tìm:              │
    │   1. Quy định về học phí     │
    │   2. Deadline thanh toán     │
    │                              │
    │   → Sẽ call Retriever tool   │
    │   → Rồi verify answer        │
    │   → Rồi generate response"   │
    │                              │
    │   ✓ Intelligent acting       │
    │   ✓ Multi-step reasoning     │
    │   ✓ Tool orchestration       │
    └──────────────────────────────┘
                   │
                   ▼
            Answer with confidence
```

**Agent = AI that decides WHAT to do and WHEN to do it**
(Not just following fixed pipeline)

---

## 2. ReACT Pattern (Recommended for Project)

### 2.1 ReACT = Reasoning + Acting

```
REACT Loop:

Step 1: THOUGHT
"Hmm, user asks about tuition. I should search for tuition info."
(Agent thinks about what to do)

Step 2: ACTION
"I will call RetrievalTool with query: 'tuition fee first year'"
(Agent decides which tool to use)

Step 3: OBSERVATION
Tool returns: ["Doc1 about tuition", "Doc2 about payment deadline", ...]
(Agent sees result of action)

Step 4: THOUGHT (again)
"Good! I found tuition info. Do I have enough? 
 Actually, I also need payment deadline...
 Or is payment deadline implied in the tuition doc? Let me check."
(Re-evaluate)

Step 5: ACTION (maybe again)
Could:
  - "Do another search for deadline"
  - OR "Generate answer with what I have"
(Decide next action)

Step 6: ANSWER
"Based on documents [Doc1, Doc2], the tuition is..."
(Final response)

Max iterations: 5 (prevent infinite loops)
```

### 2.2 ReACT Prompt Template

```python
REACT_PROMPT = """
You are a helpful AI assistant for answering student regulation questions.

You have access to the following tools:

1. RetrievalTool: Search the knowledge base
   Usage: Retrieve("query about topic")
   
2. VerificationTool: Check if answer is sufficient
   Usage: Verify(answer, confidence_threshold=0.75)

Think step-by-step about what you need to do.

Use the following format:

Question: [the input question you must answer]
Thought: [you should always think about what to do]
Action: [the action to take, should be one of [Retrieve, Verify, Answer]]
Action Input: [the input to the action]
Observation: [the result of the action]
... (this Thought/Action/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: [the final answer to the original input question]

Begin!

Question: {input}
Thought:"""

```

---

## 3. Tools: Actions Agent Can Take

### 3.1 Tool #1: RetrievalTool

```python
from langchain.tools import Tool, tool

@tool
def retrieval_tool(query: str) -> str:
    """
    Search the knowledge base for documents related to the query.
    Returns the most relevant documents.
    """
    # Call retriever
    docs = retriever.retrieve(query)
    
    # Format results
    result = "Retrieved the following documents:\n"
    for i, doc in enumerate(docs):
        result += f"\nDoc {i+1}: {doc.metadata['source']}\n"
        result += f"Content: {doc.page_content[:500]}...\n"
    
    return result

# Tool definition
retrieval_tool_def = Tool(
    name="Retrieval",
    func=retrieval_tool,
    description="Useful for finding information in the knowledge base"
)
```

### 3.2 Tool #2: VerificationTool

```python
@tool
def verification_tool(answer: str, confidence: float = 0.75) -> dict:
    """
    Verify if an answer is sufficient based on confidence threshold.
    
    Args:
        answer: The candidate answer
        confidence: Confidence threshold (0-1)
    
    Returns: {"sufficient": True/False, "reason": "..."}
    """
    # Use simple heuristic or LLM to check
    # For now: simple heuristic
    
    if len(answer) < 50:
        return {
            "sufficient": False,
            "reason": "Answer too short, likely incomplete"
        }
    
    if "I don't know" in answer:
        return {
            "sufficient": False,
            "reason": "Answer indicates insufficient information"
        }
    
    return {
        "sufficient": True,
        "reason": "Answer appears comprehensive"
    }

verification_tool_def = Tool(
    name="Verification",
    func=verification_tool,
    description="Check if an answer is sufficient"
)
```

### 3.3 Tool #3: QueryRefinerTool

```python
@tool
def refine_query(query: str) -> str:
    """
    Reformulate query to find better results.
    Tries synonyms and expansions.
    """
    # LLM reformulates query
    prompt = f"""
    The user asked: "{query}"
    
    Generate 3 alternative ways to ask this same question 
    (using different keywords/synonyms):
    """
    
    alternatives = llm(prompt)
    return alternatives

refine_query_tool = Tool(
    name="RefineQuery",
    func=refine_query,
    description="Alternative formulations of the query"
)

# Example:
# Input: "Học lại được không?"
# Output: [
#   "Có thể retake môn được không?",
#   "Đăng ký học lại một môn",
#   "Điều kiện học lại môn"
# ]
```

---

## 4. Agent Initialization

### 4.1 Create Agent with LangChain

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain.llms import Ollama

# 1. Initialize LLM
llm = Ollama(
    model="mistral",
    base_url="http://localhost:11434",
    temperature=0.3  # Low = deterministic
)

# 2. Define tools
tools = [
    retrieval_tool_def,
    verification_tool_def,
    refine_query_tool
]

# 3. Create agent
from langchain.prompts import PromptTemplate

react_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    template=REACT_PROMPT  # Defined above
)

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=react_prompt
)

# 4. Wrap in executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=5,
    early_stopping_method="generate",
    verbose=True  # Print reasoning
)

# 5. Run
response = agent_executor.invoke({
    "input": "Học phí năm nhất bao nhiêu?"
})
```

### 4.2 Full Agent Integration Code

```python
# src/agent/orchestrator.py

from langchain.agents import create_react_agent, AgentExecutor
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from src.retrieval.retriever import HybridRetriever

class StudentChatbotAgent:
    def __init__(self, retriever_path="./data/chroma"):
        # Initialize LLM
        self.llm = Ollama(
            model="mistral",
            base_url="http://localhost:11434",
            temperature=0.3
        )
        
        # Initialize retriever
        self.retriever = HybridRetriever(kb_path=retriever_path)
        
        # Setup tools
        self.tools = self._setup_tools()
        
        # Create agent
        self._setup_agent()
    
    def _setup_tools(self):
        """Define available tools"""
        
        @tool("Retrieve")
        def retrieve_docs(query: str) -> str:
            docs = self.retriever.retrieve(query)
            result = "Retrieved documents:\n"
            for doc in docs:
                result += f"- {doc.source}: {doc.page_content[:200]}...\n"
            return result
        
        @tool("Verify")
        def verify_answer(answer: str) -> str:
            if len(answer.split()) < 20:
                return "Answer too short. Need more detail."
            return "Answer looks sufficient."
        
        return [retrieve_docs, verify_answer]
    
    def _setup_agent(self):
        """Setup ReACT agent"""
        
        prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad"],
            template=REACT_PROMPT  # Your template
        )
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=5,
            early_stopping_method="generate",
            verbose=True
        )
    
    def answer_question(self, question: str) -> dict:
        """Main entry point"""
        
        try:
            response = self.executor.invoke({
                "input": question
            })
            
            return {
                "answer": response["output"],
                "success": True
            }
        
        except Exception as e:
            return {
                "answer": f"Error: {str(e)}",
                "success": False
            }
```

---

## 5. Iteration Flow with State Management

### 5.1 Tracking Agent State

```python
class AgentState:
    def __init__(self, query: str):
        self.query = query
        self.iterations = 0
        self.thoughts = []
        self.actions = []
        self.observations = []
        self.confidence = 0.0
        self.answer = None
    
    def add_iteration(self, thought, action, observation):
        self.iterations += 1
        self.thoughts.append(thought)
        self.actions.append(action)
        self.observations.append(observation)
    
    def set_answer(self, answer, confidence):
        self.answer = answer
        self.confidence = confidence
    
    def to_dict(self):
        return {
            "query": self.query,
            "iterations": self.iterations,
            "final_answer": self.answer,
            "confidence": self.confidence,
            "steps": [
                {"thought": t, "action": a, "observation": o[:200]}
                for t, a, o in zip(
                    self.thoughts,
                    self.actions,
                    self.observations
                )
            ]
        }
```

### 5.2 Example Iteration Flow

```
[AGENT STATE]
Query: "Học phí năm nhất bao nhiêu?"
Iterations: 0
Confidence: 0.0

─── ITERATION 1 ───
Thought: "I need to find tuition info for first-year students"
Action: RETRIEVE("tuition first year")
Observation: "Found 5 docs about tuition"
  → [Regulations.pdf, Policy.txt, ...]
Confidence: 0.65 (only partial info)

─── ITERATION 2 ───
Thought: "I have basic tuition info, 
          but need to verify if this is complete"
Action: RETRIEVE("tuition payment deadline first year")
Observation: "Found 3 docs with payment info"
Confidence: 0.88 (looks complete)

─── ITERATION 3 ───
Thought: "I have sufficient info now. Time to answer"
Action: ANSWER()
Final Answer: "Tuition for first year is 8 million VND.
               Payment deadline is September 15."
Confidence: 0.90 ✓

─── END ───
Total iterations: 3
```

---

## 6. Confidence Scoring

### 6.1 How to Calculate Confidence

```python
def calculate_confidence(state: AgentState) -> float:
    """
    Calculate confidence of the agent's answer.
    
    Factors:
    - Number of relevant docs retrieved
    - Consistency across docs
    - Specific vs vague language
    - LLM's self-reported confidence
    """
    
    score = 0.0
    weights = {}
    
    # Factor 1: Doc count (0-0.3)
    doc_count = len(state.observations[-1].split("Doc "))
    if doc_count >= 3:
        weights["doc_count"] = 0.3
    elif doc_count >= 1:
        weights["doc_count"] = 0.2
    else:
        weights["doc_count"] = 0.1
    
    # Factor 2: Answer specificity (0-0.4)
    answer = state.answer
    if any(keyword in answer for keyword in ["million", "date", "deadline", "%"]):
        weights["specificity"] = 0.4  # Specific answer
    else:
        weights["specificity"] = 0.2  # Generic answer
    
    # Factor 3: Iterations needed (0-0.3)
    if state.iterations <= 2:
        weights["iterations"] = 0.3  # Quick answer = confident
    elif state.iterations <= 4:
        weights["iterations"] = 0.2
    else:
        weights["iterations"] = 0.1  # Too many iterations = less conf
    
    # Combine
    total_weight = sum(weights.values())
    if total_weight > 0:
        score = sum(weights.values()) / total_weight
    
    return min(score, 1.0)  # Cap at 1.0
```

### 6.2 Confidence Thresholds

```python
if confidence >= 0.85:
    status = "HIGH - Answer ready to return"
elif confidence >= 0.70:
    status = "MEDIUM - OK but could be better"
else:
    status = "LOW - Insufficient information"
    # Consider: refining query, searching different angles, etc.
```

---

## 7. Error Handling

### 7.1 Common Error Scenarios

```python
class AgentErrorHandler:
    
    @staticmethod
    def handle_no_results(query, retriever):
        """No relevant docs found"""
        # Try refined query
        refined = refine_query(query)
        for refined_q in refined:
            new_docs = retriever.retrieve(refined_q)
            if new_docs:
                return new_docs
        
        # Still no results
        return {
            "error": "NO_RESULTS",
            "message": "Could not find relevant information",
            "suggestion": f"Try asking about: ..."
        }
    
    @staticmethod
    def handle_conflicting_docs(docs):
        """Docs contradict each other"""
        # Flag to user
        return {
            "error": "CONFLICTING_INFO",
            "message": "Found conflicting information in sources",
            "docs": docs,
            "suggestion": "Please verify with official source"
        }
    
    @staticmethod
    def handle_max_iterations(state):
        """Max iterations reached without answer"""
        return {
            "error": "MAX_ITERATIONS",
            "answer": state.answer or "Unable to provide complete answer",
            "partial": True,
            "iterations": state.iterations
        }
```

---

## 8. Testing Agent

### 8.1 Test Cases

```python
test_queries = [
    {
        "query": "Học phí năm nhất bao nhiêu?",
        "expected_contains": ["million", "VND", "tuition"],
        "expected_confidence": 0.80
    },
    {
        "query": "Còn được học lại không nếu điểm dưới C?",
        "expected_contains": ["retake", "grade", "C"],
        "expected_confidence": 0.75
    },
    {
        "query": "Scholarship là gì?",
        "expected_contains": ["scholarship", "award", "eligible"],
        "expected_confidence": 0.78
    }
]

def test_agent(agent, test_cases):
    for test in test_cases:
        print(f"\nTesting: {test['query']}")
        
        result = agent.answer_question(test['query'])
        answer = result['answer']
        
        # Check content
        contains_all = all(
            keyword.lower() in answer.lower()
            for keyword in test['expected_contains']
        )
        print(f"  Contains expected keywords: {'✓' if contains_all else '✗'}")
        
        # Will show iterations
        print(f"  Success: {result.get('success', False)}")
```

---

## 9. Logging Agent Activity

```python
import json
from datetime import datetime

def log_agent_activity(state: AgentState, user_id: str):
    """Log agent reasoning for debugging"""
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "query": state.query,
        "iterations": state.iterations,
        "steps": state.to_dict()["steps"],
        "confidence": state.confidence,
        "answer": state.answer,
        "latency_ms": 0  # Will be filled by caller
    }
    
    # Save to log
    with open("logs/agent_activity.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    # Also track in DB for analytics
    save_to_database(log_entry)
```

---

## Summary 📝

| Concept | Purpose |
|---------|---------|
| **ReACT** | Pattern for agent reasoning |
| **Thought** | Agent thinks about what to do |
| **Action** | Agent calls a tool |
| **Observation** | Agent sees tool result |
| **Tools** | Retrieve, Verify, Refine, etc. |
| **Confidence** | Score of answer quality |
| **Iterations** | Loop until answer found (max 5) |
| **Error Handling** | Graceful fallbacks |

---

## Next Steps

🔗 **Related Files:**
- `09-Prompt-Engineering.md` - Optimize prompts for Agent
- `04-System-Architecture.md` - Where Agent fits in system
- `02-AgenticRAG-Architecture.md` - Agent concepts
