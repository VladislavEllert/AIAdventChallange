import re
from .config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_fixed(
    text: str,
    source: str,
    title: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    strategy: str = "fixed",
) -> list[dict]:
    words = text.split()
    step = size - overlap
    chunks = []
    i = 0
    idx = 0
    while i < len(words):
        window = words[i : i + size]
        chunks.append(
            {
                "text": " ".join(window),
                "source": source,
                "title": title,
                "section": title,
                "strategy": strategy,
                "idx": idx,
            }
        )
        idx += 1
        i += step
    return chunks


def chunk_structural(
    text: str,
    source: str,
    title: str,
    max_section_words: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    splits = list(heading_re.finditer(text))

    sections = []
    for i, m in enumerate(splits):
        start = m.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        level = len(m.group(1))
        heading = m.group(2).strip()
        body = text[start:end].strip()
        sections.append((level, heading, body))

    if not sections:
        return chunk_fixed(text, source, title, strategy="structural")

    chunks = []
    idx = 0
    heading_stack: list[str] = []

    for level, heading, body in sections:
        heading_stack = heading_stack[: level - 1] + [heading]
        section_path = " > ".join(heading_stack)

        words = body.split()
        if len(words) <= max_section_words:
            chunks.append(
                {
                    "text": body,
                    "source": source,
                    "title": title,
                    "section": section_path,
                    "strategy": "structural",
                    "idx": idx,
                }
            )
            idx += 1
        else:
            sub = chunk_fixed(body, source, title, strategy="structural")
            for c in sub:
                c["section"] = section_path
                c["idx"] = idx
                idx += 1
                chunks.append(c)

    return chunks
