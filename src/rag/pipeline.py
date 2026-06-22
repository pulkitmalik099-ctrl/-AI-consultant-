import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.retrieval.vector_store import get_store

_PROMPT = ChatPromptTemplate.from_template(
    """You are an expert Benefits Administration consultant copilot.
Answer the question using ONLY the provided context from internal business documents.
Cite the source document for each piece of information you use.
If the answer is not found in the context, say exactly:
"I don't have that information in the indexed documents."

Context:
{context}

Question: {question}
Answer:"""
)


def _format_docs(docs: list) -> str:
    return "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


def ask(question: str) -> dict:
    retriever = get_store().as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(question)

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)
    chain = _PROMPT | llm | StrOutputParser()

    answer = chain.invoke({"context": _format_docs(docs), "question": question})

    sources = sorted({doc.metadata.get("source", "unknown") for doc in docs})
    return {"answer": answer, "sources": sources}
