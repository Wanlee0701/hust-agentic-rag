# 📚 DOCUMENTATION GUIDE - Student Regulation Chatbot (AgenticRAG)

Welcome! This folder contains **comprehensive documentation** for building an AI-powered student regulation chatbot using **AgenticRAG architecture** with **local models** for privacy.

---

## 📖 How to Use These Docs

### **Phase 1: Learning & Understanding (Week 1)**

Read in this order to grasp concepts before coding:

1. **`01-RAG-Fundamentals.md`** ⭐ START HERE
   - Learn what RAG is and why it's useful
   - Understand semantic vs keyword search
   - **Time: 30 min**

2. **`02-AgenticRAG-Architecture.md`**
   - Advanced: Agent reasoning loop
   - When/how to refine queries
   - **Time: 45 min**

3. **`03-CLIR-Multilingual.md`**
   - Handle Vietnamese & English
   - Cross-lingual retrieval
   - **Time: 30 min**

4. **`04-System-Architecture.md`**
   - See how components connect
   - Data flow: query → answer
   - **Time: 30 min**

5. **`05-Tech-Stack-Explanation.md`**
   - Why Ollama, LangChain, Chroma?
   - Trade-off decisions explained
   - **Time: 30 min**

✅ **After these 5 files, you understand the architecture!**

---

### **Phase 2: Implementation (Weeks 2-5)**

Reference docs while building each component:

6. **`06-Data-Preparation-Guide.md`** - Start implementation
   - Extract PDFs → chunks → embeddings → vector store
   - Build knowledge base
   - **Reference while coding data pipeline**

7. **`07-Retrieval-Component.md`**
   - Implement semantic + BM25 hybrid search
   - Re-ranking and edge cases
   - **Reference while coding retriever**

8. **`08-Agent-Design.md`**
   - Build ReACT agent with reasoning loop
   - Tool orchestration
   - **Reference while coding agent**

9. **`09-Prompt-Engineering.md`**
   - Optimize prompts for better results
   - Few-shot examples
   - **Reference while optimizing LLM calls**

---

### **Phase 3: Testing & Deployment (Weeks 5-6)**

Before going live:

10. **`10-Testing-Strategy.md`**
    - Unit, integration, E2E tests
    - Manual QA test cases
    - Evaluation metrics
    - **Reference before release**

11. **`11-Deployment-Guide.md`**
    - Local development setup (30 min)
    - Docker deployment
    - Health checks & monitoring
    - **Reference for setup & deployment**

12. **`12-API-Reference.md`** (Optional)
    - Build REST API wrapper
    - Integration with other systems
    - **Reference if need API**

---

## 🚀 Quick Start (Copy-Paste Timeline)

### **Estimated Time: 6 Weeks**

```
Week 1:
  Mon-Tue: Read docs 01-05 (theory)
  Wed: Understand architecture
  Thu-Fri: Environment setup (Ollama, Python, venv)

Week 2:
  Mon-Wed: Data preparation (PDF → KB)
  Thu-Fri: Retriever implementation

Week 3-4:
  Mon-Wed: Agent development
  Thu-Fri: Prompt engineering & testing

Week 5:
  Mon-Wed: Full E2E testing (50+ manual cases)
  Thu-Fri: Performance optimization

Week 6:
  Mon-Tue: Final testing & bug fixes
  Wed-Thu: Deployment setup
  Fri: Demo & presentation ready
```

---

## 📋 File Purpose Summary

| File | Purpose | When to Read | Time |
|------|---------|-------------|------|
| **01-RAG-Fundamentals** | Understand RAG basics | Start | 30 min |
| **02-AgenticRAG-Arch** | Learn Agent concept | Week 1 | 45 min |
| **03-CLIR-Multilingual** | Handle languages | Week 1 | 30 min |
| **04-System-Arch** | See big picture | Week 1 | 30 min |
| **05-Tech-Stack** | Why each tech | Week 1 | 30 min |
| **06-Data-Prep** | Build KB | Week 2 | Reference |
| **07-Retriever** | Implement search | Week 2-3 | Reference |
| **08-Agent-Design** | Code agent | Week 3-4 | Reference |
| **09-Prompts** | Optimize LLM | Week 4 | Reference |
| **10-Testing** | Test everything | Week 5 | Reference |
| **11-Deploy** | Setup production | Week 6 | Reference |
| **12-API** | Optional API | After release | Reference |

---

## 🎯 Key Concepts (TL;DR)

### **What You're Building**

```
┌─────────────────────────────────────────────────┐
│  CHATBOT: Answer student regulation questions   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Input: "Học phí bao nhiêu?"                   │
│                ↓                                │
│  ┌─────────────────────────────────────────────┐
│  │ Main Flow:                                  │
│  │ 1. Agent thinks: "Need tuition info"       │
│  │ 2. Retriever searches KB (hybrid search)   │
│  │ 3. Gets 5 relevant docs                    │
│  │ 4. Agent verifies: "Do I have enough?"     │
│  │ 5. LLM generates answer from docs          │
│  └─────────────────────────────────────────────┘
│                ↓                                │
│  Output: "Học phí năm nhất 8 triệu VND... 
│           (Source: regulations.pdf)"           │
│                                                 │
│  All local → Private → Accurate → Fast         │
│                                                 │
└─────────────────────────────────────────────────┘
```

### **3 Main Technologies**

1. **Ollama + Mistral 7B** (Local LLM)
   - Run on your machine
   - No cloud, no API keys
   - Privacy-first

2. **LangChain** (Agent framework)
   - Orchestrate everything
   - Handle tool calls
   - Manage reasoning loop

3. **Chroma** (Vector database)
   - Store embeddings
   - Fast semantic search
   - Local files (no server)

---

## 💾 Project Structure

After setup:

```
chatbot-project/
├── docs/                          ← You are here!
│   ├── 01-RAG-Fundamentals.md
│   ├── 02-AgenticRAG-Architecture.md
│   ├── ... (all 12 files)
│   └── README.md                  ← This file
│
├── src/
│   ├── agent/                     # Agent logic
│   ├── retrieval/                 # Search components
│   ├── embeddings/                # Embedding generation
│   ├── main.py                    # Entry point
│   └── api/                       # (Optional) REST API
│
├── knowledge_base/
│   └── raw/                       # Your PDF files here
│
├── data/
│   ├── chroma/                    # Vector store (auto-created)
│   └── embeddings.pkl             # Cached embeddings
│
├── tests/                         # Test files
│
├── requirements.txt               # Python dependencies
├── config.yaml                    # Configuration
├── docker-compose.yml             # Docker setup
└── README.md                      # Project README
```

---

## ⚡ Key Learnings

### **Before You Start**
- [ ] Understand RAG (read doc 01)
- [ ] Know Agent concept (read doc 02)
- [ ] Appreciate multilingual support (read doc 03)

### **While Building**
- [ ] Use hybrid retrieval (semantic + keyword)
- [ ] Limit agent iterations (max 5)
- [ ] Test with real Vietnamese + English queries
- [ ] Monitor latency (<3s per query)

### **Before Release**
- [ ] Run 50+ manual test cases
- [ ] Achieve >80% accuracy
- [ ] Measure metrics (precision, recall, F1)
- [ ] Test error cases (no results, ambiguous queries)

---

## 🔗 Cross-References

Docs reference each other. When reading:

- **Concept questions?** → See 01-RAG-Fundamentals, 02-AgenticRAG
- **Architecture questions?** → See 04-System-Architecture
- **Why tech choice?** → See 05-Tech-Stack-Explanation
- **How to code X?** → See 06-12 (implementation docs)
- **Deployment?** → See 11-Deployment-Guide

---

## 📞 Troubleshooting

**Getting confused?**
1. Re-read the specific section in relevant doc
2. Check crosslinks at bottom of each file
3. Run the examples in the implementation docs

**Test not passing?**
→ See 10-Testing-Strategy.md for debugging

**Setup issues?**
→ See 11-Deployment-Guide.md for common problems

**Integration questions?**
→ See 12-API-Reference.md for API usage

---

## 🎓 Learning Tips

1. **Read all of Week 1 docs first** (01-05)
   - Don't rush to code
   - Understand concepts
   - Ask questions

2. **Implementation is reference** (06-12)
   - Don't memorize
   - Refer as you code
   - Follow examples

3. **Google-Friendly**
   - Docs use common terminology
   - Easy to search forums for help
   - LangChain + Ollama well-documented

4. **Copy-Paste, Then Understand**
   - Grab code examples
   - Run them
   - Read code to understand
   - Modify for your case

---

## 📅 Recommended Reading Schedule

### **Day 1-2: Theory (Read 01-05)**
- Morning: 01-RAG-Fundamentals
- Afternoon: 02-AgenticRAG-Architecture
- Next day AM: 03-CLIR-Multilingual
- Next day PM: 04-System-Architecture

### **Day 3: Understanding (Re-read 05)**
- Full day: 05-Tech-Stack-Explanation
- Setup environment (11-Deployment-Guide quick start)

### **Week 2-5: Implementation (Reference 06-09)**
- Reference docs as you code
- Build component by component
- Run examples

### **Week 5-6: Testing & Release (Use 10-11)**
- Reference 10-Testing-Strategy for QA
- Use 11-Deployment-Guide for setup

---

## ✅ Success Criteria

After completing everything:

- [ ] You can explain RAG to someone else
- [ ] You built a working chatbot locally
- [ ] It answers test questions >80% accuracy
- [ ] It handles both Vietnamese & English
- [ ] You can deploy it (Docker or local)
- [ ] You know how to test & optimize it
- [ ] You're ready for production! 🚀

---

## 🆘 Getting Help

1. **Stuck on theory?** → Re-read relevant doc section
2. **Code not working?** → Check examples in implementation docs
3. **Architecture question?** → See 04-System-Architecture
4. **Need troubleshooting?** → See 11-Deployment-Guide
5. **Integration help?** → See 12-API-Reference

---

## 🎉 You're Ready!

This comprehensive documentation covers **everything** you need to build a professional-grade AI chatbot. 

**Start with doc 01, follow the schedule, and you'll have a working system in 6 weeks!**

Happy coding! 🚀

---

**Questions?** Check the "Next Steps" section at the bottom of each file for cross-references!
