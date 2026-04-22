# Docker Deployment

Docker is free to use locally. Public hosting can be free on some platforms, but free tiers usually sleep, restart, or limit storage.

This project can run in two Docker modes.

Mode 1: local development with Docker Compose:

- `backend`: FastAPI API on port `8000`
- `frontend`: Streamlit UI on port `8501`

Mode 2: public web hosting with one Docker web service:

- FastAPI runs internally on port `8000`
- Streamlit runs on the hosting platform's `$PORT`
- The public link opens the Streamlit UI
- Streamlit calls FastAPI through `http://127.0.0.1:8000`

## Run Locally

Create or update `.env` with your keys:

```env
HUGGINGFACEHUB_API_TOKEN=your_hugging_face_token
GROQ_API_KEY=your_groq_key
SECRET_KEY=change-this-secret-for-production
```

Start both services:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8501
```

Backend health check:

```text
http://localhost:8000/health
```

The Chroma vector store is kept in the Docker volume `chroma_data`, so it survives normal container restarts.

## Run Like A Cloud Web Service

This uses the Dockerfile default command and runs both FastAPI and Streamlit in one container:

```bash
docker build -t role-based-ragchatbot .
docker run --env-file .env -p 8501:8501 role-based-ragchatbot
```

Open:

```text
http://localhost:8501
```

## Useful Commands

Stop containers:

```bash
docker compose down
```

Stop containers and delete the Chroma volume:

```bash
docker compose down -v
```

Rebuild after changing dependencies:

```bash
docker compose up --build
```

## Hosting Notes

For a resume demo, deploy the Dockerfile as one web service on Render, Railway, Fly.io, or a VPS.

Required environment variables on the hosting platform:

```text
HUGGINGFACEHUB_API_TOKEN
GROQ_API_KEY
SECRET_KEY
PINECONE_API_KEY
VECTOR_STORE_PROVIDER=pinecone
```

Optional environment variables:

```text
TOKEN_EXPIRE_MINUTES
RAG_TOP_K
RAG_MIN_RELEVANCE_SCORE
CHROMA_COLLECTION
PINECONE_INDEX_NAME
PINECONE_NAMESPACE
PINECONE_CLOUD
PINECONE_REGION
PINECONE_DIMENSION
PINECONE_METRIC
HF_EMBEDDING_MODEL
GROQ_MODEL
```

On platforms that provide a `PORT` environment variable, the container exposes Streamlit on that port automatically.

For cloud deployment, use Pinecone:

```text
VECTOR_STORE_PROVIDER=pinecone
PINECONE_INDEX_NAME=role-based-ragchatbot
PINECONE_NAMESPACE=company-docs
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_DIMENSION=1024
PINECONE_METRIC=cosine
```

Set `PINECONE_DIMENSION` to the dimension returned by your embedding endpoint. The currently tested Hugging Face endpoint returns 1024-dimensional vectors, so this project defaults to `1024`.

With Pinecone, vectors are stored in Pinecone instead of `/app/resources/vectorstore`, so the Docker container does not need persistent disk. The app still reads source files from `resources/data` when it needs to build or rebuild the Pinecone index.

If you use Chroma instead, use persistent storage for `/app/resources/vectorstore` if you do not want Chroma to rebuild after restarts. Without persistent storage, the app can still rebuild the vector store from `resources/data`, but the first chat request may be slower.

Never bake `.env` into the Docker image. Add API keys as environment variables in the hosting dashboard.
