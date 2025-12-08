# text_utils.py
import re, unicodedata

def prepare_xtts_text(text: str) -> str:
    """Normalize quotes, Unicode, collapse spaces."""
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    text = unicodedata.normalize('NFKC', text)
    return re.sub(r'\s+', ' ', text).strip()


def split_text_xtts(text: str, max_chars: int = 250) -> list[str]:
    """
    Split text into chunks ≤ max_chars for XTTS.
    • Prefers splits on sentence endings (. ! ?), then clauses (, ; : - —), then words.
    • Merges tiny chunks (<30 chars) if possible.
    • Never cuts words.
    • Forces space after periods if missing.
    """
    min_len = 30

    print(f"\n[XTTS SPLIT] ORIGINAL TEXT ({len(text)} chars):")
    print(f"{text}")

    # --- 1. CLEAN TEXT ---
    text = prepare_xtts_text(text)
    text = re.sub(r'\.(?=[^\s])', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"\n[XTTS SPLIT] CLEANED TEXT ({len(text)} chars):")
    print(f"{text}")
    # ---------------------

    if len(text) <= max_chars:
        print(f"\n[XTTS SPLIT] SINGLE CHUNK (≤ {max_chars} chars) → returning 1 chunk")
        return [text]

    # --- 2. SPLIT INTO SENTENCES ---
    sentences = re.split(r'(?<=[.!?])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    print(f"\n[XTTS SPLIT] Split into {len(sentences)} sentence(s):")
    for i, s in enumerate(sentences, 1):
        print(f"  [{i}] {len(s):3d} chars: {s}")
    # -------------------------------

    # --- 3. BUILD CHUNKS HIERARCHICALLY ---
    chunks = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            clauses = re.split(r'(?<=[,;:\-—])\s*', sentence)
            clauses = [c.strip() for c in clauses if c.strip()]
            for clause in clauses:
                if len(clause) > max_chars:
                    words = clause.split()
                    sub = ""
                    for word in words:
                        test = (sub + " " + word).strip() if sub else word
                        if len(test) > max_chars:
                            if sub:
                                if current and len(current + " " + sub) <= max_chars:
                                    current = (current + " " + sub).strip()
                                else:
                                    if current:
                                        chunks.append(current)
                                        current = ""
                                    chunks.append(sub)
                            sub = word
                        else:
                            sub = test
                    if sub:
                        if current and len(current + " " + sub) <= max_chars:
                            current = (current + " " + sub).strip()
                        else:
                            if current:
                                chunks.append(current)
                                current = ""
                            current = sub
                else:
                    test = (current + " " + clause).strip() if current else clause
                    if len(test) > max_chars:
                        if current:
                            chunks.append(current)
                            current = ""
                        current = clause
                    else:
                        current = test
        else:
            test = (current + " " + sentence).strip() if current else sentence
            if len(test) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                current = sentence
            else:
                current = test

    if current:
        chunks.append(current)

    print(f"\n[XTTS SPLIT] After building: {len(chunks)} chunk(s)")

    i = 0
    merges = 0
    while i < len(chunks) - 1:
        if len(chunks[i + 1]) < min_len:
            test = (chunks[i] + " " + chunks[i + 1]).strip()
            if len(test) <= max_chars:
                chunks[i] = test
                del chunks[i + 1]
                merges += 1
                continue
        i += 1
    if merges:
        print(f"[XTTS SPLIT] Merged {merges} tiny chunk(s)")

    print(f"\n[XTTS SPLIT] FINAL RESULT: {len(chunks)} chunk(s)")
    total_chars = 0
    for idx, chunk in enumerate(chunks, 1):
        total_chars += len(chunk)
        print(f"\n  === CHUNK {idx} === ({len(chunk)} chars)")
        print(f"{chunk}")
        print(f"  {'─' * 50}")
    print(f"\n[XTTS SPLIT] TOTAL CHARACTERS IN ALL CHUNKS: {total_chars}")
    return chunks

def split_text_fish(text: str, max_chars: int = 250) -> list[str]:
    """
    Split text into chunks ≤ max_chars for Fish Speech.
    • Prefers splits on sentence endings (. ! ?), then clauses (, ; : - —), then words.
    • Merges tiny chunks (<30 chars) if possible.
    • Never cuts words.
    • Forces space after periods if missing.
    """
    min_len = 30

    print(f"\n[FISH SPLIT] ORIGINAL TEXT ({len(text)} chars):")
    print(f"{text}")

    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\.(?=[^\s])', '. ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"\n[FISH SPLIT] CLEANED TEXT ({len(text)} chars):")
    print(f"{text}")

    if len(text) <= max_chars:
        print(f"\n[FISH SPLIT] SINGLE CHUNK (≤ {max_chars} chars) → returning 1 chunk")
        return [text]

    sentences = re.split(r'(?<=[.!?])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    print(f"\n[FISH SPLIT] Split into {len(sentences)} sentence(s):")
    for i, s in enumerate(sentences, 1):
        print(f"  [{i}] {len(s):3d} chars: {s}")

    chunks = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            clauses = re.split(r'(?<=[,;:\-—])\s*', sentence)
            clauses = [c.strip() for c in clauses if c.strip()]
            for clause in clauses:
                if len(clause) > max_chars:
                    words = clause.split()
                    sub = ""
                    for word in words:
                        test = (sub + " " + word).strip() if sub else word
                        if len(test) > max_chars:
                            if sub:
                                if current and len(current + " " + sub) <= max_chars:
                                    current = (current + " " + sub).strip()
                                else:
                                    if current:
                                        chunks.append(current)
                                        current = ""
                                    chunks.append(sub)
                            sub = word
                        else:
                            sub = test
                    if sub:
                        if current and len(current + " " + sub) <= max_chars:
                            current = (current + " " + sub).strip()
                        else:
                            if current:
                                chunks.append(current)
                                current = ""
                            current = sub
                else:
                    test = (current + " " + clause).strip() if current else clause
                    if len(test) > max_chars:
                        if current:
                            chunks.append(current)
                            current = ""
                        current = clause
                    else:
                        current = test
        else:
            test = (current + " " + sentence).strip() if current else sentence
            if len(test) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                current = sentence
            else:
                current = test

    if current:
        chunks.append(current)

    print(f"\n[FISH SPLIT] After building: {len(chunks)} chunk(s)")

    i = 0
    merges = 0
    while i < len(chunks) - 1:
        if len(chunks[i + 1]) < min_len:
            test = (chunks[i] + " " + chunks[i + 1]).strip()
            if len(test) <= max_chars:
                chunks[i] = test
                del chunks[i + 1]
                merges += 1
                continue
        i += 1
    if merges:
        print(f"[FISH SPLIT] Merged {merges} tiny chunk(s)")

    print(f"\n[FISH SPLIT] FINAL RESULT: {len(chunks)} chunk(s)")
    total_chars = 0
    for idx, chunk in enumerate(chunks, 1):
        total_chars += len(chunk)
        print(f"\n  === CHUNK {idx} === ({len(chunk)} chars)")
        print(f"{chunk}")
        print(f"  {'─' * 50}")
    print(f"\n[FISH SPLIT] TOTAL CHARACTERS IN ALL CHUNKS: {total_chars}")
    return chunks


def split_text_kokoro(text: str, max_chars: int = 500) -> list[str]:
    """
    Kokoro ≥500 chars safe → use the same aggressive hierarchical splitter
    as XTTS/Fish for maximum efficiency.
    """
    min_len = 40   

    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\.(?=[^\s])', '. ', text)  
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks = []
    current = ""

    for sentence in sentences:
        if len(sentence) > max_chars:
            clauses = re.split(r'(?<=[,;:\-—])\s*', sentence)
            clauses = [c.strip() for c in clauses if c.strip()]

            for clause in clauses:
                if len(clause) > max_chars:
                    words = clause.split()
                    sub = ""
                    for word in words:
                        test = (sub + " " + word).strip() if sub else word
                        if len(test) > max_chars:
                            if sub:
                                if current and len(current + " " + sub) <= max_chars:
                                    current = (current + " " + sub).strip()
                                else:
                                    if current:
                                        chunks.append(current)
                                        current = ""
                                    chunks.append(sub)
                            sub = word
                        else:
                            sub = test
                    if sub:
                        if current and len(current + " " + sub) <= max_chars:
                            current = (current + " " + sub).strip()
                        else:
                            if current:
                                chunks.append(current)
                                current = ""
                            current = sub
                else:
                    test = (current + " " + clause).strip() if current else clause
                    if len(test) > max_chars:
                        if current:
                            chunks.append(current)
                            current = ""
                        current = clause
                    else:
                        current = test
        else:
            # normal sentence
            test = (current + " " + sentence).strip() if current else sentence
            if len(test) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                current = sentence
            else:
                current = test

    if current:
        chunks.append(current)

    i = 0
    while i < len(chunks) - 1:
        if len(chunks[i + 1]) < min_len:
            test = (chunks[i] + " " + chunks[i + 1]).strip()
            if len(test) <= max_chars:
                chunks[i] = test
                del chunks[i + 1]
                continue            
        i += 1

    return chunks



def sanitize_for_whisper(text: str) -> str:
    """Lower-case, keep only a-z 0-9 and spaces."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()