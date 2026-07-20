# 02. AgenticRAG Architecture - Agent + Reasoning Loop

## 📚 Mục Tiêu
Hiểu **AgenticRAG** - RAG với AI Agent tự động reasoning & quyết định cách tìm kiếm, để xử lý **câu hỏi phức tạp** mà RAG cơ bản không giải quyết được.

---

## 1. Vấn Đề: Khi Nào RAG Cơ Bản Không Đủ?

### 1.1 Ví Dụ: Câu Hỏi Phức Tạp

**Question:** "Nếu tôi đã học 2 năm và chưa đạt GPA 2.0, quy định gì áp dụng? Có thể hoãn học được không?"

**RAG Truyền Thống:**
```
[RETRIEVER] Search for: "GPA 2.0" → Find docs
[LLM] Answer: "GPA 2.0 là điều kiện học tiếp"
❌ Nhưng không trả lời: "Có thể hoãn được?"
```

**Tại sao thất bại?**
1. Query quá phức tạp → retriever không biết tìm "hoãn học" (synonym của query gốc?)
2. Cần **kết hợp** multiple pieces of info từ nhiều docs khác nhau
3. Cần **verify** answer từ preliminary search trước khi generate final answer

---

## 2. Giải Pháp: Agentic RAG

### 2.1 Khái Niệm
**AgenticRAG = RAG + AI Agent with Autonomous Reasoning Loop**

```
┌──────────────────────────────────────────────────────────────┐
│             AGENTIC RAG WORKFLOW                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User Query: "Có thể hoãn học không nếu GPA < 2.0?"        │
│      │                                                       │
│      ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [AGENT] Think & Plan (using LLM)                        ││
│  │ "Hmm, cần tìm 2 thứ:                                    ││
│  │  1. GPA requirement                                      ││
│  │  2. Deferment/hoãn học policy"                          ││
│  │                                                          ││
│  │ → Decide: Retrieve with queries:                        ││
│  │   Query1: "GPA 2.0 requirement"                         ││
│  │   Query2: "deferment policy"                            ││
│  └─────────────────────────────────────────────────────────┘│
│      │                                                       │
│      ▼                                                       │
│  [ITERATION 1] Retrieve for Query1                          │
│  └─ Find: ["Section3-Academic...", "GPA-Policy..."]        │
│     Extract: "GPA must be ≥ 2.0"                           │
│                                                              │
│      ▼                                                       │
│  [ITERATION 2] Retrieve for Query2                          │
│  └─ Find: ["Section5-Deferment..."]                        │
│     Extract: "Deferment allowed up to 1 year"              │
│                                                              │
│      ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ [AGENT] Combine & Reason                                ││
│  │ Info gathered:                                           ││
│  │  • GPA < 2.0 → cannot continue normally                 ││
│  │  • But deferment available up to 1 year                 ││
│  │                                                          ││
│  │ Decision: Answer question ✓                             ││
│  │ (Check if enough info, or need more retrieval)          ││
│  └─────────────────────────────────────────────────────────┘│
│      │                                                       │
│      ▼                                                       │
│  [GENERATION] Create Final Answer                           │
│  "Yes, you CAN defer learning. According to Section5,       │
│   deferment allowed up to 1 year. GPA < 2.0 prevents        │
│   normal continuation but deferment resolves this."         │
│   (Sources: Section3, Section5)                             │
│                                                              │
│      │                                                       │
│      ▼                                                       │
│  Answer with Confidence ✓                                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### A) Agent (Tác Nhân Quyết Định)
**Là gì:** LLM-powered module tự động quyết định hành động tiếp theo
**Trách Nhiệm:**
- Hiểu user query
- Planning: "Tôi cần tìm thông tin gì?"
- **Decide**: Nên call retrieval tool? Nên refine query? Có đủ info answer?
- Verify: Answer tốt chưa?

**Pseudocode:**
```python
Agent Loop:
  while not done:
    thought = LLM.think(query, retrieved_docs)
    # "Hmm, I have info about GPA, but not deferment..."
    
    decision = LLM.decide(thought)
    # "Decision: RETRIEVE with refine_query"
    
    if decision == "RETRIEVE":
      refined_query = LLM.refine_query(query, thought)
      new_docs = retriever.search(refined_query)
      retrieved_docs.extend(new_docs)
      
    elif decision == "ANSWER":
      answer = LLM.generate(query, retrieved_docs)
      return answer
      
    elif decision == "REFINE":
      query = LLM.reformulate(query)
      # Try different retrieval approach
```

#### B) Reasoning Loop
**Là gì:** Vòng lặp: Think → Decide → Act → Update

**Iteration Example:**
```
Iteration 0 (Initial):
  Thought: "Need info about GPA and deferment"
  Decision: "Retrieve with 2 search queries"
  Action: Call Retriever(Q1, Q2)
  Result: Get docs, but only for Q1
  
Iteration 1 (Refine):
  Thought: "Got GPA info, but deferment query might be wrong. 
            Try synonym: 'postpone studying'"
  Decision: "Retrieve with synonym"
  Action: Call Retriever("postpone studying")
  Result: Found deferment docs!
  
Iteration 2 (Decision Point):
  Thought: "Now have both GPA and deferment info. 
            Can generate confident answer."
  Decision: "ANSWER"
  Action: Generate final answer
  Result: Return answer to user ✓

Max Iterations: 3-5 (prevent infinite loops)
```

#### C) Tools (Action Space)
Agent có thể call các tools:

| Tool | Purpose | Returns |
|------|---------|---------|
| **RetrievalTool** | Search KB cho documents | Top-K docs + scores |
| **RefinementTool** | Rephrase query thành synonyms | Better query |
| **VerificationTool** | Check answer consistency | Score 0-1 |
| **ExtractionTool** | Extract key facts từ docs | Structured data |

---

## 3. AgenticRAG vs RAG Cơ Bản

### 3.1 So Sánh Detailed

```
┌─────────────────────┬──────────────┬─────────────────────┐
│ Aspect              │ RAG          │ AgenticRAG          │
├─────────────────────┼──────────────┼─────────────────────┤
│ Decision Making     │ Fixed (1-hop)│ Dynamic (reasoning) │
│ Iteration           │ 1x           │ Multiple (≤5)       │
│ Query Refinement    │ ❌ No        │ ✅ Yes              │
│ Tool Usage          │ Just Retriev-│ Multiple tools      │
│                     │ al           │                     │
│ Complex Questions   │ ⚠️ Limited   │ ✅ Supported        │
│ Latency             │ ~500ms       │ ~2-5s (more iters)  │
│ Setup Complexity    │ Medium       │ High (need LLM call)│
│ Best For            │ Simple Q&A   │ Complex reasoning   │
└─────────────────────┴──────────────┴─────────────────────┘
```

### 3.2 Workflow Comparison

**RAG (Single-hop):**
```
Query → [Search KB] → [LLM Generate] → Answer
```

**AgenticRAG (Multi-step):**
```
Query → [Agent Planning] → Loop:
          ├─ [Retrieve & Reason]
          ├─ [Check Sufficiency]
          ├─ If not enough: Refine → Re-retrieve
          └─ If enough: Generate Answer
          → Answer
```

---

## 4. Implement AgenticRAG: Key Decisions

### 4.1 Agent Type

#### Option A: ReACT (Reasoning + Act)
```
Thought → Action → Observation → Thought → ...
```
**Pros:** Clear reasoning, easy to debug
**Cons:** More LLM calls

#### Option B: Step-Back Prompting
```
First thought about high-level approach
then search and execute
```
**Pros:** Better abstraction
**Cons:** Need good prompt engineering

#### Option C: Tree of Thoughts
```
        Query
        /   \
     Branch1 Branch2
      / \     / \
    ...  ...  ... ...
```
**Pros:** Explore multiple reasoning paths
**Cons:** Expensive (many LLM calls)

**For DỰ ÁN:** Use **ReACT** - balanced, clear

### 4.2 When to Stop Iterating
**Termination Conditions:**

1. **Confidence Threshold**
   ```
   if answer_confidence > 0.85:
       stop and return
   ```

2. **Max Iterations**
   ```
   if iteration_count >= 5:
       stop (force generate)
   ```

3. **No New Information**
   ```
   if new_docs_retrieved == 0 and iteration > 1:
       stop (refinement not helping)
   ```

---

## 5. Ứng Dụng cho Dự Án

### 5.1 Phù Hợp với Dự Án Không?
✅ **YES** - Vì quy chế sinh viên có nhiều câu hỏi phức tạp:
- "Nếu tôi drop 2 môn, GPA sẽ... còn... được học tiếp?"
- "Scholarship có thể combine được với khoán không?"
- "Điểm dưới C im thế nào?"

❌ **Trade-off:** Chậm hơn (2-5s vs 500ms), phức tạp hơn để implement

### 5.2 Example in Project

**Simplified AgenticRAG for Student Chatbot:**

```
User: "Có thế learn lại được môn C nếu học ở khóa sau không?"

Agent Loop:
  Iteration 1:
    Thought: "Need info about retake policy & course prerequisites"
    Retrieve: ["Retake Policy", "Prerequisites"]
    Result: Found retake = OK, but need "retake timing"
    
  Iteration 2:
    Thought: "Found retake OK, but when can retake? Need specific timeline"
    Retrieve: [refined:"semester planning", "graduation timeline"]
    Result: Found "can retake next semester" ✓
    
  Decision: "Have enough info"
  Answer: "Yes, you can learn C again next semester. 
           Per policy [Source], course retakes allowed..."
```

---

## 6. Implementation Checklist

- [ ] Implement Agent decision logic (ReACT prompts)
- [ ] Create Tools: Retriever, Refiner, Verifier
- [ ] Setup Reasoning Loop with max iterations
- [ ] Error handling: No docs found, low confidence
- [ ] Logging: Track each iteration, decisions
- [ ] Test: Simple Q & Complex Q
- [ ] Optimize: Balance accuracy vs speed

---

## Summary 📝

| Concept | Giải Thích |
|---------|-----------|
| **AgenticRAG** | RAG + autonomous reasoning agent + iteration loop |
| **When to Use** | Complex Q that need multi-step reasoning |
| **vs RAG** | More powerful but slower, requires agent design |
| **Agent** | LLM-powered, decides when to retrieve/refine/answer |
| **Reasoning Loop** | Think → Decide → Act → Check → Repeat (≤5x) |
| **Tools** | Retriever, Refiner, Verifier, etc. |
| **For Project** | Good for complex regulation QA, but add 2-3s latency |

---

## Next Steps

🔗 **Related Files:**
- `03-CLIR-Multilingual.md` - How to handle Vietnamese & English queries
- `04-System-Architecture.md` - Full system design with AgenticRAG
- `08-Agent-Design.md` - Detailed agent implementation
- `09-Prompt-Engineering.md` - Agent prompt templates
