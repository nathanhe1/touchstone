"""Character vocabulary shared by the toy models, environments and probes."""

PAD, BOS, EOS = 0, 1, 2
CHARS = "0123456789+-=?|>abcdefghijklmnopqrstuvwxyz "
STOI = {c: i + 3 for i, c in enumerate(CHARS)}
ITOS = {i: c for c, i in STOI.items()}
VOCAB_SIZE = len(CHARS) + 3
MAX_OUT = 8  # max generated characters per answer


def encode(s: str) -> list[int]:
    return [STOI[c] for c in s if c in STOI]


def decode(ids) -> str:
    out = []
    for i in ids:
        i = int(i)
        if i == EOS:
            break
        if i in ITOS:
            out.append(ITOS[i])
    return "".join(out)
