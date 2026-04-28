import streamlit as st
import os
import time
import shutil
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

# --- 1. DYNAMIC CONFIGURATION ---
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DATA_PATH = os.getenv("PDF_DATA_PATH", "/app/data")
CHROMA_PATH = "/app/chroma_db"

st.set_page_config(page_title="3GPP AI Assistant", layout="wide")

# --- 2. FORCED INGESTION LOGIC ---
@st.cache_resource
def force_ingest_and_load(_embeddings):
    """Wipes old DB and recreates it every time the app initializes."""
    if os.path.exists(CHROMA_PATH):
        # We use a small delay and retries to handle Windows file locks
        shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    
    if not os.path.exists(DATA_PATH) or not os.listdir(DATA_PATH):
        st.error(f"No PDFs found in {DATA_PATH}. Please add 3GPP specs.")
        return None

    with st.status("🔄 Fresh Ingestion: Chunking & Embedding Specs..."):
        loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
        docs = loader.load()
        
        # Using your preferred high-quality chunking settings
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, 
            chunk_overlap=300,
            separators=["\n\n", "\n", ".", " "]
        )
        chunks = text_splitter.split_documents(docs)
        
        # Create fresh vector store
        db = Chroma.from_documents(
            documents=chunks, 
            embedding=_embeddings, 
            persist_directory=CHROMA_PATH
        )
        st.success(f"Successfully indexed {len(chunks)} chunks from {len(docs)} PDFs.")
        return db

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Engineering Console")
    selected_model = st.selectbox("Select LLM Model", ["llama3.2", "gemma3:4b"])
    st.info("Note: This app re-indexes your data folder on every fresh session.")

# --- 4. MAIN CHAT INTERFACE ---
st.title("📑 3GPP Packet Core Expert")
st.caption(f"Connected to {selected_model} (Self-Ingesting Mode)")

# Initialize Embeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)

# Trigger the automatic ingestion
db = force_ingest_and_load(embeddings)

query = st.chat_input("Ask a technical question about the specs...")

if query and db:
    llm = OllamaLLM(
        model=selected_model, 
        base_url=OLLAMA_URL, 
        num_ctx=8192, 
        temperature=0.1
    )

    with st.spinner("Thinking..."):
        # Retrieval
        start_time = time.perf_counter()
        results = db.similarity_search(query, k=10)
        
        # Generation
        context = "\n\n".join([d.page_content for d in results])
        template = """
        ### [SYSTEM INSTRUCTION]
        You are an 3GPP expert Packet Core Engineer. Explain the technical flow based on the context.
        
        ### [CONTEXT]
        {context}
        
        ### [USER QUESTION]
        {question}
        
        ### [RESPONSE]
        """
        prompt = template.format(context=context, question=query)
        response = llm.invoke(prompt)
        
        total_time = time.perf_counter() - start_time

    # Display Result
    st.chat_message("assistant").write(response)
    st.caption(f"⏱️ Total Response Latency: {total_time:.2f}s")
