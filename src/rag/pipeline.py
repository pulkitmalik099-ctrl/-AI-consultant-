import json
import os
import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
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


def _llm(streaming: bool = False) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0,
        streaming=streaming,
    )


# ---------------------------------------------------------------------------
# Sync ask (used by /chat)
# ---------------------------------------------------------------------------

def ask(question: str, session_id: str = "default") -> dict:
    from src.analytics.logger import log_query

    t0 = time.monotonic()
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
    log_query(session_id, question, answer, sources, (time.monotonic() - t0) * 1000)
    return {"answer": answer, "sources": sources, "session_id": session_id}


# ---------------------------------------------------------------------------
# Async streaming ask (used by /chat/stream)
# ---------------------------------------------------------------------------

async def ask_stream(question: str, session_id: str = "default"):
    """AsyncGenerator yielding SSE-ready JSON strings."""
    from src.analytics.logger import log_query

    t0 = time.monotonic()
    retriever = get_store().as_retriever(search_kwargs={"k": 5})
    docs = await retriever.ainvoke(question)
    sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})

    history = get_session_history(session_id)
    messages = _RAG_PROMPT.format_messages(
        context=_format_docs(docs),
        question=question,
        history=history.messages,
    )

    llm = _llm(streaming=True)
    full_answer = ""

    async for chunk in llm.astream(messages):
        if chunk.content:
            full_answer += chunk.content
            yield json.dumps({"chunk": chunk.content})

    history.add_message(HumanMessage(content=question))
    history.add_message(AIMessage(content=full_answer))

    log_query(session_id, question, full_answer, sources, (time.monotonic() - t0) * 1000)
    yield json.dumps({"done": True, "sources": sources, "session_id": session_id})


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------

def summarize(source: str) -> dict:
    store = get_store()
    docs = store.similarity_search(source, k=10)
    filtered = [d for d in docs if source.lower() in d.metadata.get("source", "").lower()]
    context_docs = filtered if filtered else docs

    chain = _SUMMARIZE_PROMPT | _llm() | StrOutputParser()
    summary = chain.invoke({"context": _format_docs(context_docs)})
    return {"summary": summary, "source": source, "chunks_used": len(context_docs)}
