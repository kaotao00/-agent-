# Interview Guide

## How to Introduce the Project

This project is a multi-agent intelligent tender generation system for construction engineering bidding scenarios. It combines enterprise knowledge retrieval, specialized agent collaboration, shared memory, rule validation, and pricing tool integration to reduce tender preparation time and improve consistency.

## Suggested 3-Minute Walkthrough

1. Start from the problem:
   traditional tender preparation depends on scattered historical files, budget data, qualification materials, and repeated manual collaboration.
2. Explain the architecture:
   a project manager agent parses the tender request and dispatches tasks to technical, budget, business, and compliance agents.
3. Explain the knowledge layer:
   historical tenders, construction norms, pricing documents, and qualification materials are stored in a knowledge base. Retrieval is exposed through a local fallback retriever and an optional LangChain + Milvus retriever.
4. Explain consistency control:
   shared memory stores critical facts like duration, qualification, and quoted total. A compliance agent checks section completeness and cross-agent consistency.
5. Explain engineering value:
   the backend is exposed through FastAPI, the frontend can demonstrate the workflow live, and the system can later connect to real enterprise pricing or document systems.

## Code Mapping

- `tender_system/service.py`: service entry, demo payload, search and generation orchestration
- `tender_system/retrieval.py`: local retriever and optional LangChain + Milvus retriever
- `tender_system/agents.py`: agent roles, shared memory, and pricing tool
- `tender_system/orchestrator.py`: overall multi-agent workflow
- `tender_system/api.py`: FastAPI endpoints and static page hosting
- `frontend/index.html`: interactive demo page

## High-Frequency Interview Questions

### Why not use one single LLM prompt?

Because tender generation is multi-domain and strongly constrained. Technical content, pricing, business qualifications, and compliance checks have different responsibilities and different correctness criteria. Multi-agent decomposition improves controllability and consistency.

### What is the value of RAG here?

Tender content must be grounded in enterprise documents and norms. RAG reduces hallucination and improves traceability by retrieving historical tender templates, pricing guidance, and qualification materials before generation.

### How do you avoid conflicts between agents?

Shared memory stores canonical facts such as duration, qualification level, and quote amount. The compliance agent then performs explicit rule checks against both the request and the generated sections.

### Why add tool invocation for pricing?

Budget content should not rely only on natural language generation. It needs structured calculations and enterprise pricing logic. Tool invocation is a safer pattern for integrating quota pricing systems.

### What is production-ready vs demo-ready in this project?

The current version is demo-ready and service-ready. For production, I would add authentication, persistent vector storage, real document parsing, workflow observability, versioned prompts, and a review/approval process.
