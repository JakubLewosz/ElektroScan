import hashlib

PALETTE = [
    "#ff5577",
    "#45d483",
    "#38bdf8",
    "#f97316",
    "#a78bfa",
    "#facc15",
    "#2dd4bf",
    "#fb7185",
    "#84cc16",
    "#60a5fa",
    "#f472b6",
    "#c6a87c",
]


def get_symbol_color(symbol_name: str) -> str:
    digest = hashlib.sha256(symbol_name.encode("utf-8")).digest()
    return PALETTE[digest[0] % len(PALETTE)]
