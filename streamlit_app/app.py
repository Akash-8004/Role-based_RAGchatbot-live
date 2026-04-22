import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
SOURCE_CODE_URL = os.getenv(
    "SOURCE_CODE_URL",
    "https://github.com/Akash-8004/Role-based_RAGchatbot",
)

ROLE_COLORS = {
    "engineering": "#2563eb",
    "marketing": "#c026d3",
    "finance": "#059669",
    "hr": "#ea580c",
    "employee": "#475569",
    "executive": "#7c3aed",
}

SAMPLE_PROMPTS = {
    "engineering": "What is the high-level system architecture?",
    "marketing": "Summarize the 2024 campaign ROI and customer acquisition.",
    "finance": "What was the Q2 marketing spend and vendor cost?",
    "hr": "Show employee attendance and salary related insights.",
    "employee": "What is the work from home policy?",
    "executive": "Compare Q4 revenue, marketing performance, HR, and engineering priorities.",
}

DEMO_PASSWORDS = {
    "tony": "password123",
    "bruce": "securepass",
    "sam": "financepass",
    "natasha": "hrpass123",
    "steve": "employeepass",
    "pepper": "executivepass",
}


def api_post(path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = httpx.post(f"{API_BASE_URL}{path}", json=payload, headers=headers, timeout=45)
    response.raise_for_status()
    return response.json()


def api_get(path: str, token: str | None = None) -> dict | list:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = httpx.get(f"{API_BASE_URL}{path}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def role_badge(role: str, label: str | None = None) -> str:
    color = ROLE_COLORS.get(role, "#475569")
    text = label or role.title()
    return (
        f"<span class='role-badge' style='background:{color}18; color:{color}; "
        f"border-color:{color}40'>{text}</span>"
    )


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for source in sources:
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">{source['source']}</div>
                    <div class="source-meta">
                        {role_badge(source['department'], source['department'])}
                        <span>score {source['score']}</span>
                    </div>
                    <p>{source['snippet']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def submit_prompt(prompt: str) -> None:
    st.session_state.pending_prompt = prompt


def stat_card(label: str, value: str, detail: str = "") -> str:
    return f"""
    <div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
        <div class="stat-detail">{detail}</div>
    </div>
    """


st.set_page_config(page_title="RBAC RAG Chatbot", page_icon="lock", layout="wide")

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        max-width: 1120px;
    }
    .app-header {
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 1rem;
        margin-bottom: 1.2rem;
    }
    .app-title {
        font-size: 2.1rem;
        font-weight: 760;
        letter-spacing: 0;
        color: #111827;
        margin: 0;
    }
    .app-subtitle {
        color: #4b5563;
        font-size: 1rem;
        margin-top: .35rem;
    }
    .role-badge {
        display: inline-flex;
        align-items: center;
        border: 1px solid;
        border-radius: 999px;
        padding: .16rem .55rem;
        font-size: .78rem;
        font-weight: 650;
        white-space: nowrap;
    }
    .source-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: .8rem .9rem;
        margin-bottom: .7rem;
        background: #ffffff;
    }
    .source-title {
        font-weight: 720;
        color: #111827;
        margin-bottom: .35rem;
    }
    .source-meta {
        display: flex;
        gap: .5rem;
        align-items: center;
        color: #64748b;
        font-size: .82rem;
        margin-bottom: .45rem;
    }
    .source-card p {
        color: #374151;
        margin: 0;
        line-height: 1.45;
    }
    .stat-card {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        padding: .9rem 1rem;
        border-radius: 8px;
        min-height: 96px;
    }
    .stat-label {
        color: #64748b;
        font-size: .82rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: .04em;
    }
    .stat-value {
        color: #111827;
        font-size: 1.55rem;
        font-weight: 780;
        line-height: 1.25;
        margin-top: .22rem;
    }
    .stat-detail {
        color: #64748b;
        font-size: .85rem;
        margin-top: .2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "token" not in st.session_state:
    st.session_state.token = None
if "profile" not in st.session_state:
    st.session_state.profile = None
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "selected_demo_username" not in st.session_state:
    st.session_state.selected_demo_username = None
if "password_value" not in st.session_state:
    st.session_state.password_value = ""

st.markdown(
    """
    <div class="app-header">
        <h1 class="app-title">Internal RBAC RAG Chatbot</h1>
        <div class="app-subtitle">
            Ask company questions with department-aware retrieval and source-backed answers.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Access")
    st.markdown(f"Source code: [{SOURCE_CODE_URL}]({SOURCE_CODE_URL})")

    try:
        demo_users = api_get("/demo-users")
    except Exception:
        demo_users = []
        st.warning("Start the FastAPI server before logging in.")

    if demo_users:
        user_labels = {
            f"{user['full_name']} ({user['role']})": user["username"] for user in demo_users
        }
        selected_label = st.selectbox("Demo user", list(user_labels))
        username = user_labels[selected_label]
        if st.session_state.selected_demo_username != username:
            st.session_state.selected_demo_username = username
            st.session_state.password_value = DEMO_PASSWORDS.get(username, "")
        password = st.text_input("Password", type="password", key="password_value")
    else:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password", key="password_value")

    sign_in, clear_chat = st.columns(2)
    with sign_in:
        sign_in_clicked = st.button("Sign in", use_container_width=True)
    with clear_chat:
        clear_clicked = st.button("Clear", use_container_width=True)

    if sign_in_clicked:
        try:
            auth = api_post("/auth/login", {"username": username, "password": password})
            st.session_state.token = auth["access_token"]
            st.session_state.profile = api_get("/me", st.session_state.token)
            st.session_state.messages = []
            st.success(f"Signed in as {auth['role_label']}")
        except httpx.HTTPStatusError as exc:
            st.error(exc.response.json().get("detail", "Login failed."))
        except Exception as exc:
            st.error(f"Could not connect to API: {exc}")

    if clear_clicked:
        st.session_state.messages = []

    if st.session_state.profile:
        profile = st.session_state.profile
        st.divider()
        st.markdown("**Current user**")
        st.markdown(profile["full_name"])
        st.markdown(role_badge(profile["role"], profile["role_label"]), unsafe_allow_html=True)

        st.markdown("**Allowed departments**")
        st.markdown(
            " ".join(role_badge(department, department) for department in profile["allowed_departments"]),
            unsafe_allow_html=True,
        )

        try:
            health = api_get("/health")
            st.divider()
            st.markdown("**RAG status**")
            st.caption(f"{health['chunks_indexed']} chunks indexed")
            st.caption(f"Embeddings: {health['embedding_model']}")
            st.caption(f"LLM: {health['generation_model']}")
        except Exception:
            st.caption("RAG index status unavailable.")

        if st.button("Log out", use_container_width=True):
            st.session_state.token = None
            st.session_state.profile = None
            st.session_state.messages = []
            st.session_state.pending_prompt = None
            st.rerun()

if not st.session_state.token:
    left, right = st.columns([1.2, 1])
    with left:
        st.info("Sign in from the sidebar to start chatting with role-filtered company data.")
    with right:
        st.markdown("**Try these demo roles**")
        st.write("Finance, Marketing, HR, Engineering, and Employee each retrieve different documents.")
    st.stop()

profile = st.session_state.profile
top_left, top_mid, top_right = st.columns(3)
with top_left:
    st.markdown(
        stat_card("Role", profile["role_label"], f"Signed in as {profile['username']}"),
        unsafe_allow_html=True,
    )
with top_mid:
    st.markdown(
        stat_card(
            "Departments",
            str(len(profile["allowed_departments"])),
            ", ".join(profile["allowed_departments"]),
        ),
        unsafe_allow_html=True,
    )
with top_right:
    st.markdown(
        stat_card("Messages", str(len(st.session_state.messages)), "Current chat session"),
        unsafe_allow_html=True,
    )

st.markdown("**Quick prompts**")
prompt_cols = st.columns(2)
sample_prompt = SAMPLE_PROMPTS.get(profile["role"])
if sample_prompt:
    with prompt_cols[0]:
        if st.button(sample_prompt, use_container_width=True):
            submit_prompt(sample_prompt)
with prompt_cols[1]:
    custom_example = "Which sources were used for this answer?"
    if st.button(custom_example, use_container_width=True):
        submit_prompt(custom_example)

st.divider()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []))

typed_prompt = st.chat_input("Ask a question about company data...")
prompt = st.session_state.pending_prompt or typed_prompt
st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving role-approved context and generating answer..."):
            try:
                result = api_post("/chat", {"message": prompt}, st.session_state.token)
                answer = result["answer"]
                st.markdown(answer)
                render_sources(result.get("sources", []))
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": result.get("sources", []),
                    }
                )
            except httpx.HTTPStatusError as exc:
                st.error(exc.response.json().get("detail", "Chat request failed."))
            except Exception as exc:
                st.error(f"Could not connect to API: {exc}")
