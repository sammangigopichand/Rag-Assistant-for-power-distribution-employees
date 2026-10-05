import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=5,
            initial_delay=1,
            max_delay=8,
            exp_base=2,
            jitter=1,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        )
    ),
)


def generate_answer(question: str, context: str, direct: bool = False):

    prompt = f"{question}\n\nRetrieved document context:\n{context}" if direct else f"""
You are an AI knowledge assistant for utility employees.

Answer the employee's question using ONLY the provided context.

If the answer is not available in the context, say:

"I could not find this information in the available knowledge base."

Do not invent information.

Format the answer in clean Markdown.

Formatting rules:
- Use short headings when useful.
- Use bullet points for lists.
- Use numbered lists for procedures or steps.
- Use **bold text** for important terms.
- Keep paragraphs short.
- Do not write one large paragraph.
- Do not use excessive decoration.
- Make the answer easy for employees to scan quickly.

Employee Question:
{question}

Context:
{context}

Provide a clear, concise, well-structured answer.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low")
        ),
    )

    return response.text
