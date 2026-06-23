"""build_index.py — (re)build the ChromaDB SOP index from QC-SOP.md.

Run on the GPU box after `git pull` (the index lives on D:\ and is not
committed). Delegates to rag.build_index(). STUB.
"""
from __future__ import annotations


def main() -> None:
    from agent_core import rag

    rag.build_index()


if __name__ == "__main__":
    main()
