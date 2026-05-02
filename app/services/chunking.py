from dataclasses import dataclass

import tiktoken


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    text: str


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_tokens: int,
    overlap_tokens: int,
    model_name: str,
) -> list[TextChunk]:
    if overlap_tokens >= chunk_tokens:
        raise ValueError("overlap_tokens must be smaller than chunk_tokens")

    encoding = _encoding_for_model(model_name)
    chunks: list[TextChunk] = []
    chunk_index = 0

    stride = chunk_tokens - overlap_tokens

    for page_number, text in pages:
        tokens = encoding.encode(text)
        start = 0
        while start < len(tokens):
            current = tokens[start : start + chunk_tokens]
            chunks.append(
                TextChunk(
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=encoding.decode(current),
                )
            )
            chunk_index += 1
            if start + chunk_tokens >= len(tokens):
                break
            start += stride

    return chunks


def _encoding_for_model(model_name: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")
