from app.services.rag import rebuild_vector_store


def main() -> None:
    result = rebuild_vector_store()
    print(f"Indexed {result['chunks_indexed']} chunks into {result['collection']}.")
    print(f"Vector store: {result['vector_store']}")


if __name__ == "__main__":
    main()
