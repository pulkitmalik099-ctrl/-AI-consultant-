import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from src.retrieval.vector_store import get_store
from src.rag.memory import get_session_history

_RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert Benefits Administration consultant copilot.
Answer the question using ONLY the provided context from internal business documents.
Cite the source document for each piece of information you use.
If the answer is not found in the context, say exactly:
"I don't have that information in the indexed documents."

Context:
{context}"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

_SUMMARIZE_PROMPT = ChatPromptTemplate.from_template(
    """Summarize the following document content in a structured format.
Include: purpose, key topics, main requirements, and important details.

Content:
{context}

Structured Summary:"""
)


def _format_docs(docs: list) -> str:
    return "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


def _llm() -> ChatOpenAI:
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)


def ask(question: str, session_id: str = "default") -> dict:
    retriever = get_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(question)

    chain = _RAG_PROMPT | _llm() | StrOutputParser()
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )

    answer = chain_with_history.invoke(
        {"context": _format_docs(docs), "question": question},
        config={"configurable": {"session_id": session_id}},
    )

    sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})
    return {"answer": answer, "sources": sources, "session_id": session_id}


def summarize(source: str) -> dict:
    store = get_store()
    docs = store.similarity_search(source, k=10)
    filtered = [d for d in docs if source.lower() in d.metadata.get("source", "").lower()]
    context_docs = filtered if filtered else docs

    chain = _SUMMARIZE_PROMPT | _llm() | StrOutputParser()
    summary = chain.invoke({"context": _format_docs(context_docs)})

    return {
        "summary": summary,
        "source": source,
        "chunks_used": len(context_docs),
    }
