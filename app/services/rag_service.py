from app.services.retrieval_service import search_knowledge_base
from app.services.llm_service import generate_answer


def ask_rag(question: str):

    results = search_knowledge_base(
        query=question,
        k=5
    )

    context_parts = []
    sources = []

    for result in results:

        content = result.get("content", "")

        if content.strip():
            context_parts.append(content)

        source = result.get("source")

        if source and source not in sources:
            sources.append(source)

    context = "\n\n".join(context_parts)

    print("\nRetrieved chunks:", len(results))
    print("Context chunks:", len(context_parts))
    print("Context length:", len(context))

    if not context.strip():
        return {
            "question": question,
            "answer": "No relevant context was retrieved from the knowledge base.",
            "sources": sources
        }

    answer = generate_answer(
        question=question,
        context=context
    )

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }