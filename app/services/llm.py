from openai import AsyncOpenAI

from app.config import Settings
from app.schemas import Citation


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.llm_api_key:
            raise RuntimeError("NVIDIA_API_KEY is required")
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    async def embed_texts(self, texts: list[str], input_type: str) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.settings.embedding_model,
            input=texts,
            encoding_format="float",
            extra_body={
                "input_type": input_type,
                "modality": "text",
            },
        )
        return [item.embedding for item in response.data]

    async def answer_question(self, question: str, citations: list[Citation]) -> str:
        context = "\n\n".join(
            f"Page {citation.page_number}:\n{citation.text}"
            for citation in citations
        )
        response = await self.client.chat.completions.create(
            model=self.settings.generation_model,
            temperature=self.settings.generation_temperature,
            top_p=self.settings.generation_top_p,
            max_tokens=self.settings.generation_max_tokens,
            stream=self.settings.generation_stream,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer questions using only the supplied PDF context. "
                        "If the context does not contain the answer, say you do not know. "
                        "Format answers in clean Markdown using this structure:\n"
                        "**Summary**: one sentence direct answer.\n"
                        "**Key points**:\n"
                        "- 2 to 4 concise bullets, only if they add value.\n"
                        "Keep wording simple and user-friendly. "
                        "Avoid repeating the question and do not include raw chunk IDs or scores."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion:\n{question}",
                },
            ],
        )

        if self.settings.generation_stream:
            answer_parts: list[str] = []
            async for chunk in response:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                if delta.content is not None:
                    answer_parts.append(delta.content)
            return _normalize_answer("".join(answer_parts))

        return _normalize_answer(response.choices[0].message.content or "")


def _normalize_answer(answer: str) -> str:
    normalized = answer.replace("\r\n", "\n").strip()
    while "\n\n\n" in normalized:
        normalized = normalized.replace("\n\n\n", "\n\n")
    return normalized
