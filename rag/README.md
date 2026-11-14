# Retrieval-augmented investigation

The implemented mode is [Vector RAG](vector/README.md): verified knowledge
preparation, embeddings, persistent retrieval and bounded investigation generation.
Its guide contains local setup, commands, artifact restoration and handoff.

Shared model execution and policy belong to [ai/runtime](../ai/runtime/README.md).
Source acquisition and future additions belong to [datasets](../datasets/README.md).
Graph/Hybrid modes remain planned. The backend RAG endpoint remains unavailable;
this package currently provides a standalone CLI.
