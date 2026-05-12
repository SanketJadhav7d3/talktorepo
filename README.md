# 🔍 TalkToRepo: Structural Code Intelligence Engine

[![Python](https://img.shields.io/badge/Language-Python%203.9+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Tree-Sitter](https://img.shields.io/badge/Engine-Tree--Sitter-green?style=for-the-badge)](https://tree-sitter.github.io/tree-sitter/)

TalkToRepo is a high-performance code intelligence engine designed to bridge the gap between massive codebases and Large Language Models. Unlike standard text splitters that break code at arbitrary line counts, TalkToRepo uses **AST (Abstract Syntax Tree)** parsing to extract logical units, ensuring AI models receive syntactically complete context.

## 🚀 Key Features

*   **🧠 Logic-Preserving RAG**: Uses Tree-Sitter to chunk code by function/class boundaries, significantly improving LLM reasoning over standard RAG.
*   **⚡ Polyglot Performance**: Sub-millisecond parsing of C++, Java, Rust, and TS using a hybrid Python `ast` and C-based Tree-Sitter strategy.
*   **🔗 Graph-Based Analysis**: Automatically maps project-wide dependencies to provide the AI with a structural understanding of the repository.
*   **🛠 Production Tooling**: Designed for low-latency agentic workflows (compatible with LangChain and Gemini).

## 🏗 Technical Architecture

1.  **Ingestion**: Files are filtered and validated via extension mapping.
2.  **Parsing**: 
    *   **Python**: Handled via native `ast` for 100% feature compliance.
    *   **Core Polyglot**: C-bindings for Tree-Sitter provide high-speed extraction for 7+ languages.
3.  **Extraction**: Metadata (line ranges, signatures, imports) is structured for vectorization.
4.  **Semantic Retrieval**: Logical blocks are indexed into a Vector Store for context-aware AI querying.



