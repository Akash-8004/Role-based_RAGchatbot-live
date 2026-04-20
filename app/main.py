from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.rbac import ROLE_LABELS, allowed_departments_for
from app.core.security import authenticate_user, create_access_token, get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, UserProfile
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.rag import (
    RAGConfigurationError,
    generate_answer,
    make_snippet,
    rag_status,
    search_documents,
)
from app.services.users import User, list_demo_users


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Internal RAG chatbot with backend-enforced role-based access control.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, int | str]:
    return {
        "status": "ok",
        **rag_status(),
    }


@app.get("/demo-users")
def demo_users() -> list[dict[str, str]]:
    return list_demo_users()


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token, expires_at = create_access_token(user.username, user.role)
    return TokenResponse(
        access_token=token,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        role_label=ROLE_LABELS.get(user.role, user.role.title()),
        expires_at=expires_at,
    )


@app.get("/me", response_model=UserProfile)
def me(user: User = Depends(get_current_user)) -> UserProfile:
    allowed_departments = sorted(allowed_departments_for(user.role))
    return UserProfile(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        role_label=ROLE_LABELS.get(user.role, user.role.title()),
        allowed_departments=allowed_departments,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(get_current_user)) -> ChatResponse:
    allowed_departments = allowed_departments_for(user.role)
    try:
        results = search_documents(payload.message, allowed_departments=allowed_departments)
    except RAGConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filtered_results = [
        result for result in results if result.score >= settings.min_relevance_score
    ]
    try:
        answer = generate_answer(payload.message, filtered_results)
    except RAGConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    sources = [
        ChatSource(
            source=result.chunk.source,
            department=result.chunk.department,
            score=round(result.score, 4),
            snippet=make_snippet(result.chunk.text),
        )
        for result in filtered_results
    ]

    return ChatResponse(
        answer=answer,
        role=user.role,
        allowed_departments=sorted(allowed_departments),
        sources=sources,
        access_limited=False,
    )
