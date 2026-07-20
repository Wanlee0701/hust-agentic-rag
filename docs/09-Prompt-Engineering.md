# 09. Prompt Engineering - Crafting Effective Prompts for Agent & LLM

## 📚 Mục Tiêu
Master **prompt engineering** - cách viết prompts để có kết quả tốt nhất từ LLM trong chatbot của bạn.

---

## 1. Prompt Engineering Fundamentals

### 1.1 What is a Prompt?

**Prompt = Instructions + Context + Few Examples**

```
┌──────────────────────────────────────┐
│          PROMPT ANATOMY              │
├──────────────────────────────────────┤
│                                      │
│ 1. SYSTEM MESSAGE (Role + Rules)     │
│    "You are a student advisor..."    │
│    "Answer ONLY based on docs..."    │
│                                      │
│ 2. CONTEXT (Relevant info)           │
│    "Here are relevant documents:..." │
│    "[Doc1 content]"                  │
│    "[Doc2 content]"                  │
│                                      │
│ 3. FEW-SHOT EXAMPLES (Optional)      │
│    Example Q: "..."                  │
│    Example A: "..."                  │
│                                      │
│ 4. YOUR QUERY (User's question)      │
│    "User asks: ..."                  │
│                                      │
│ 5. OUTPUT INSTRUCTION (Format)       │
│    "Format your answer as: ..."      │
│                                      │
└──────────────────────────────────────┘
```

### 1.2 Prompt vs Result Quality (Real Impact)

```
Without optimization:
  Prompt: "Trả lời câu hỏi này"
  LLM: "Được, nhưng sao không cụ thể?"
  Quality: 40%

With optimization:
  Prompt: "Bạn là cố vấn sinh viên. 
           Trả lời dựa CHỈ vào documents này.
           Nếu không biết, nói 'Tôi không biết'.
           Format: [Direct answer] 
           Sources: [list docs]"
  LLM: "[Specific answer with sources]"
  Quality: 90%

→ Prompting goes a LONG way!
```

---

## 2. System-Level Prompts

### 2.1 Agent System Prompt (ReACT)

```
AGENT_SYSTEM_PROMPT = """
You are an intelligent assistant helping students with university regulations 
and policies.

Your task: Answer student questions about:
- Tuition and payment policies
- Academic regulations
- Deferment and leave policies
- Scholarship information
- Graduation requirements

IMPORTANT CONSTRAINTS:
1. You MUST use the provided tools to search for information
2. Answer ONLY based on information from the knowledge base
3. If information is not found, say: "I don't have this information"
4. Always cite the source of information
5. Be accurate and helpful
6. If multiple sources exist, combine them for a complete answer

You have access to tools:
- Retrieve: Search the knowledge base
- Verify: Check if your answer is sufficient

Use the ReACT format:
Thought: [What do I need to do?]
Action: [Which tool to use?]
Action Input: [Input for the tool]
Observation: [Result]

Think step by step. You can use multiple tools if needed.
"""
```

### 2.2 Generation System Prompt (After Retrieval)

```
GENERATION_SYSTEM_PROMPT = """
You are a helpful student advisor assistant.

RULES:
1. Provide accurate, helpful information
2. Base ALL answers on the provided documents
3. Do NOT make up information
4. If a question cannot be answered from documents, say so clearly
5. Be concise but thorough
6. Answer in the same language as the question
7. Include relevant sources for credibility

RESPONSE FORMAT:
- Start with a direct answer
- Provide details and context
- List relevant sources/documents
- If unclear, acknowledge it

Remember: Accuracy is more important than completeness.
If you're not sure, say so.
"""
```

---

## 3. Context-Adding Prompts

### 3.1 Retrieval Result Formatting

```python
def format_retrieved_docs(docs, query):
    """Format retrieved docs for LLM context"""
    
    context = f"""
Based on your query: "{query}"

I found the following relevant information:

"""
    
    for i, doc in enumerate(docs, 1):
        context += f"""
[Document {i}]
Source: {doc.metadata['source']}
Page: {doc.metadata.get('page', 'N/A')}
Content:
{doc.page_content}

---

"""
    
    return context
```

**Output:**
```
Based on your query: "Học phí năm nhất bao nhiêu?"

I found the following relevant information:

[Document 1]
Source: regulations_2024.pdf
Page: 12
Content:
Học phí năm nhất: 8.000.000 VND
Thời hạn thanh toán: Trước ngày 15/9

---

[Document 2]
Source: tuition_policy.txt
Page: N/A
Content:
Chính sách thanh toán học phí...

---
```

### 3.2 Relevance Filtering Prompt

```python
RELEVANCE_CHECK_PROMPT = """
Given this student query: "{query}"

Review these retrieved documents and rate their relevance:
1. Highly relevant (score: 1.0) - Directly answers the question
2. Moderately relevant (score: 0.7) - Related but not direct
3. Weakly relevant (score: 0.4) - Tangentially related
4. Not relevant (score: 0.0) - Unrelated

Documents to review:
{documents}

For each document, provide:
- Title/ID
- Relevance score (0-1)
- Brief reason

Then synthesize into a single answer using only
the highly relevant documents.
"""
```

---

## 4. Few-Shot Prompting

### 4.1 Few-Shot Examples for Q&A

```python
FEW_SHOT_QA_PROMPT = """
You are answering student questions based on university documents.

EXAMPLES:

Example 1:
Question: "Tuition payment deadline?"
Context: "Tuition deadline is September 15"
Answer: "The tuition payment deadline is September 15. 
          This applies to all first-year students. 
          Late payment may result in registration hold."

Example 2:
Question: "Can I retake a course?"
Context: "Retake allowed once per course. Grade is replaced."
Answer: "Yes, you can retake a course. Each course can be 
          retaken once, and the new grade replaces the previous one."

Example 3:
Question: "What is a GPA?"
Context: [Docs don't contain clear definition]
Answer: "I don't have a detailed explanation of GPA in the 
         available documents. I recommend asking the Registrar."

---

Now answer this question:
Question: {question}
Context: {context}
Answer:
"""
```

### 4.2 When Few-Shot Helps

**Use few-shot when:**
- Need specific format (JSON, tables, etc.)
- LLM makes mistakes on this task type
- Want consistent tone/style

**Skip few-shot when:**
- Simple straightforward questions
- Want to save tokens
- Retrieval already good

---

## 5. Output Format Specifications

### 5.1 JSON Format

```python
JSON_FORMAT_PROMPT = """
Answer the question and return ONLY valid JSON:

{
  "answer": "Direct answer here",
  "confidence": 0.85,
  "sources": [
    {
      "document": "regulations.pdf",
      "page": 12,
      "excerpt": "Relevant section..."
    }
  ],
  "follow_up_suggestion": "Optional follow-up question"
}

Question: {question}
"""
```

### 5.2 Markdown Format

```python
MARKDOWN_FORMAT_PROMPT = """
Format your answer in markdown:

## Answer
[Main answer here]

### Details
- Point 1
- Point 2
- Point 3

### Sources
- Source 1: [excerpt]
- Source 2: [excerpt]

### Related Info
[Any related policies or points]

Question: {question}
"""
```

### 5.3 Natural Language Format (Recommended)

```python
NATURAL_FORMAT_PROMPT = """
Provide a helpful, natural answer like talking to a friend:

1. Start with the direct answer
2. Add explanations and context
3. Mention relevant sources naturally
4. Keep it friendly and clear

Don't use bullet points unless really necessary.

Question: {question}
"""
```

**For DỰ ÁN:** Use natural format (best UX)

---

## 6. Instruction Clarity

### 6.1 Vague vs Clear Instructions

**❌ VAGUE:**
```
"Trả lời câu hỏi sinh viên"
"Sử dụng tài liệu được cung cấp"
"Là một cố vấn"
```
→ Result: inconsistent, may hallucinate

**✅ CLEAR:**
```
"You are answering a student question about university tuition.
 
 CONSTRAINTS:
 - Answer ONLY using the provided documents
 - Do not add information not in documents
 - Cite which document you reference
 - If not found, say clearly: 'This is not covered in available docs'
 
 Question: {question}
 Documents: {docs}
 
 Provide: [Direct answer] [Source reference]"
```

→ Result: focused, grounded, accurate

### 6.2 Tone & Style Instructions

```python
# Formal
"Provide a concise, professional response..."

# Friendly
"Explain this in a friendly, approachable way..."

# Technical
"Use precise terminology..."

# Simple
"Explain as if talking to a 10-year-old..."
```

---

## 7. Chain-of-Thought (CoT) Prompting

### 7.1 What is CoT?

**Make LLM explain its reasoning step-by-step**

```
Traditional:
  Q: "Can I skip class if I'm sick?"
  A: "Yes"  ← Direct, but how did it decide?

With CoT:
  Q: "Can I skip class if I'm sick?"
  A: "Let me think:
      1. The policy says 'students may defer class for medical reasons'
      2. The policy needs 'medical documentation'
      3. So yes, I can skip IF I provide docs
      
      Answer: Yes, you can skip class if sick, 
              but must provide medical certificate"
              
  → Better answer with reasoning!
```

### 7.2 CoT Prompt

```python
COT_PROMPT = """
Answer the question by thinking step-by-step:

Step 1: What does the question ask?
Step 2: What relevant information is in the documents?
Step 3: Is there any contradicting information?
Step 4: Synthesize into a clear answer
Step 5: What sources support this?

Question: {question}

Documents:
{documents}

Let's think step by step:
1. Question asks for:
2. Relevant info:
3. Contradictions:
4. Final answer:
5. Sources:
"""
```

---

## 8. Prompt Testing & Optimization

### 8.1 A/B Testing Prompts

```python
def compare_prompts(question, retrieval_docs):
    """A/B test different prompts"""
    
    prompts = {
        "simple": "Trả lời: {question}",
        "detailed": GENERATION_SYSTEM_PROMPT + "\n{question}",
        "cot": COT_PROMPT.format(question=question, documents=docs)
    }
    
    results = {}
    for name, prompt in prompts.items():
        answer = llm(prompt)
        results[name] = {
            "answer": answer,
            "latency_ms": measure_time(),
            "length": len(answer),
            "quality_score": evaluate(answer)  # Manual evaluation
        }
    
    return results

# Compare
results = compare_prompts("Học phí bao nhiêu?", docs)
# Results:
# {
#   "simple": {"...": ..., "quality_score": 5},
#   "detailed": {"...": ..., "quality_score": 8},
#   "cot": {"...": ..., "quality_score": 9}  # BEST
# }
```

### 8.2 Optimization Checklist

- [ ] Instructions are unambiguous
- [ ] System prompt sets clear role
- [ ] Output format specified
- [ ] Token count reasonable (not too long)
- [ ] Examples provided (if needed)
- [ ] Language consistent (Vietnamese or English)
- [ ] No contradicting instructions
- [ ] Constraints clearly stated
- [ ] Fallback for "I don't know" defined
- [ ] Tested on sample queries

---

## 9. Common Prompt Mistakes (To Avoid)

### 9.1 Mistakes & Fixes

| Mistake | Effect | Fix |
|---------|--------|-----|
| **Too vague** | "Trả lời" | Specify role, constraints, format |
| **Too long** | 1000 tokens instruction | Trim to essentials only |
| **Contradictory** | "Answer if possible" + "Must answer" | Be consistent |
| **No format spec** | Random output | Specify JSON/markdown/natural |
| **Hallucination risk** | "Use docs if available" | "ONLY use docs, never invent" |
| **No examples** | LLM guesses style | Provide few-shot examples |
| **Unclear role** | Generic response | "You are X assistant" |
| **No fallback** | LLM makes up answer | "If unknown, say 'I don't know'" |

---

## 10. Production Prompts for Your Project

### 10.1 Final Agent System Prompt

```python
FINAL_AGENT_SYSTEM_PROMPT = """
You are a helpful student advisor chatbot for university regulations.

Your responsibilities:
1. Answer questions about tuition, policies, and requirements
2. Use provided tools to search the knowledge base
3. Provide accurate, helpful information
4. Always cite sources

CRITICAL RULES:
- Answer ONLY based on provided documents
- Do NOT invent or assume information
- Do NOT go outside the knowledge base
- If uncertain, prioritize accuracy over completeness
- Always include which document supports your answer

Available Actions:
- Retrieve: Search knowledge base with queries
- Verify: Check if answer is sufficient
- Answer: Provide final response

Process:
1. Understand the question
2. Decide what information is needed
3. Retrieve from knowledge base
4. Verify you have enough information
5. Provide answer with sources

ALWAYS provide sources for credibility.
ALWAYS acknowledge if information not found.
ALWAYS answer in the language of the question.
"""
```

### 10.2 Final Generation Prompt Template

```python
FINAL_GENERATION_PROMPT = """
You are a helpful student advisor. Answer the following question 
based ONLY on the provided documents.

CONSTRAINTS:
1. Use information from documents only
2. Cite source for each fact
3. Be concise and clear
4. If information not available, say: "This is not covered in the available policies"
5. Answer in Vietnamese if question in Vietnamese, English if English

Question: {question}

Retrieved Documents:
{formatted_documents}

Your answer:
"""
```

### 10.3 Quick Reference Template

```python
def build_prompt(
    question: str,
    retrieved_docs: list,
    system_role: str = "student advisor",
    output_format: str = "natural",
    language: str = "auto"
) -> str:
    """Build optimized prompt"""
    
    prompt = f"""You are a {system_role}.

CORE RULES:
- Answer from documents ONLY
- Cite sources
- Be accurate
- Answer in {language if language != 'auto' else 'question language'}

Question: {question}

Documents:
{format_docs(retrieved_docs)}

Output format: {output_format}

Answer:
"""
    return prompt
```

---

## Summary 📝

| Technique | Use When | Benefit |
|-----------|----------|---------|
| **System Prompt** | Always | Sets role & constraints |
| **Clear Instructions** | Always | Reduces hallucination |
| **Few-Shot** | Complex tasks | Improves consistency |
| **CoT** | Complex reasoning | Better step-by-step answers |
| **Output Format** | Need structured output | Easier parsing |
| **Constraints** | Risky task | Safety guardrails |

---

## Key Takeaways 🎯

1. **Prompt engineering often > model improvement** (better prompts = better results)
2. **Be specific, clear, and constrained** (vague prompts = vague results)
3. **Always specify:** role + constraints + format + fallback
4. **Test and iterate** (A/B test different prompts)
5. **For production, use established patterns** (System + Context + Instruction)

---

## Next Steps

🔗 **Related Files:**
- `08-Agent-Design.md` - Agent uses these prompts
- `04-System-Architecture.md` - Prompts fit in system here
