import streamlit as st
import os, time
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from prometheus_client import start_http_server, Summary, Gauge

# --- PROMETHEUS METRICS ---
if "prometheus_metrics" not in st.session_state:
    st.session_state.prometheus_metrics = {
        "retrieval_time": Summary('retrieval_time_seconds', 'Time spent in retrieval and similarity search'),
        "generation_time": Summary('generation_time_seconds', 'Time spent in LLM generation'),
        "total_latency": Summary('total_latency_seconds', 'Total request time'),
    }

RETRIEVAL_TIME = st.session_state.prometheus_metrics["retrieval_time"]
GENERATION_TIME = st.session_state.prometheus_metrics["generation_time"]
TOTAL_LATENCY = st.session_state.prometheus_metrics["total_latency"]

# Start metrics server on port 8000
if "metrics_started" not in st.session_state:
    start_http_server(8000)
    st.session_state.metrics_started = True

# --- CONFIG ---
# Configuration from environment (passed by Docker/Jenkins)
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DATA_PATH = os.getenv("PDF_DATA_PATH", "/app/data")
CHROMA_PATH = os.getenv("CHROMA_PATH", "/app/chroma_db")

st.set_page_config(page_title="3GPP AI Assistant", layout="wide")
st.title("🤖 3GPP Technical Chatbot")

# Validate environment and file paths before startup

def validate_startup_config():
    errors = []
    warnings = []

    if not OLLAMA_URL:
        errors.append("OLLAMA_BASE_URL is not set.")

    data_exists = os.path.exists(DATA_PATH)
    chroma_exists = os.path.exists(CHROMA_PATH)

    if not data_exists and not chroma_exists:
        errors.append(
            f"Neither PDF data path ({DATA_PATH}) nor Chroma persistence path ({CHROMA_PATH}) exist. "
            "At least one of them must be available to initialize the app."
        )
    elif not data_exists:
        warnings.append(
            f"PDF data path does not exist: {DATA_PATH}. "
            "The app may still work if an existing Chroma DB is found at {CHROMA_PATH}."
        )
    elif not chroma_exists:
        warnings.append(
            f"Chroma persistence path does not exist: {CHROMA_PATH}. "
            "A new Chroma DB will be created from PDFs in {DATA_PATH}."
        )

    for warning in warnings:
        st.warning(warning)
    for error in errors:
        st.error(error)

    if errors:
        st.stop()


validate_startup_config()

# Sidebar settings
st.sidebar.header("Model Selection")
model_choice = st.sidebar.selectbox(
    "Choose LLM model:",
    options=["llama3.2", "gemma3:4b"],
    format_func=lambda x: x,
)
st.sidebar.write("Selected model:", model_choice)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.sidebar.header("Chat History")
for idx, item in enumerate(st.session_state.chat_history[::-1], 1):
    st.sidebar.markdown(f"**{idx}. {item['query']}**")

# --- INITIALIZATION ---
embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

@st.cache_resource
def get_llm(model_name: str):
    return OllamaLLM(model=model_name, base_url=OLLAMA_URL, num_ctx=8192, temperature=0.1)

@st.cache_resource
def get_db(persist_path: str, embedding_fn):
    if os.path.exists(persist_path):
        return Chroma(persist_directory=persist_path, embedding_function=embedding_fn)
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)
    return Chroma.from_documents(docs, embedding_fn, persist_directory=persist_path)

llm = get_llm(model_choice)
db = get_db(CHROMA_PATH, embeddings)

# Display previous responses above the input
st.markdown("## Conversation")
if st.session_state.chat_history:
    for item in st.session_state.chat_history:
        st.markdown(f"**Q:** {item['query']}")
        st.markdown(f"**A:** {item['response']}")
        st.write("---")
else:
    st.markdown("_No conversation history yet. Enter a question below._")

# User input at the bottom
with st.form(key="query_form"):
    query = st.text_input("Enter your technical question:")
    submit = st.form_submit_button("Ask")

if submit and query:
    start_total = time.perf_counter()

    with RETRIEVAL_TIME.time():
        results = db.similarity_search(query, k=15)

    context = "\n\n".join([doc.page_content for doc in results])
    prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"

    with GENERATION_TIME.time():
        response = llm.invoke(prompt)

    end_total = time.perf_counter()
    TOTAL_LATENCY.observe(end_total - start_total)

    st.session_state.chat_history.append({
        "query": query,
        "response": response,
        "model": model_choice,
        "latency": end_total - start_total,
    })

    st.rerun()

if st.session_state.chat_history:
    last_item = st.session_state.chat_history[-1]
    st.sidebar.info(f"Last query: {last_item['query']}")
    st.sidebar.info(f"Model used: {last_item['model']}")
    st.sidebar.info(f"Latency: {last_item['latency']:.2f}s")