import streamlit as st
import os
import time
import shutil
from prometheus_client import Summary, start_http_server
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

# --- 1. PROMETHEUS METRICS SETUP ---
# Start the metrics server on port 8000 for Prometheus to scrape
try:
    start_http_server(8000)
except Exception as e:
    pass # To prevent errors if port 8000 is already active during hot-reloads

S_LATENCY = Summary('search_latency_seconds', 'Time spent in vector search')
G_LATENCY = Summary('gen_latency_seconds', 'Time spent in LLM generation')

# --- 2. DYNAMIC CONFIGURATION ---
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DATA_PATH = os.getenv("PDF_DATA_PATH", "/app/data")
CHROMA_PATH = "/app/chroma_db"

st.set_page_config(page_title="3GPP AI Assistant", layout="wide")

# --- 3. CACHING FUNCTIONS ---
# Note the leading underscore '_embedding_fn' - this prevents the UnhashableParamError
@st.cache_resource
def get_db(path, _embedding_fn):
    if os.path.exists(path):
        return Chroma(persist_directory=path, embedding_function=_embedding_fn)
    return None

# --- 4. UI SIDEBAR (ADMIN & MODEL SELECTION) ---
with st.sidebar:
    st.title("⚙️ Engineering Console")
    selected_model = st.selectbox("Select LLM Model", ["llama3.2", "gemma3:4b"])
    
    st.markdown("---")
    st.subheader("Admin Operations")
    if st.button("🔄 Re-Ingest 3GPP PDFs"):
        with st.status("Processing documents..."):
            if os.path.exists(CHROMA_PATH):
                shutil.rmtree(CHROMA_PATH)
            
            # Loading and Chunking
            loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
            docs = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200, 
                chunk_overlap=300,
                separators=["\n\n", "\n", ".", " "]
            )
            chunks = text_splitter.split_documents(docs)
            
            # Indexing
            embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
            Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
            st.success(f"Ingested {len(chunks)} chunks!")
            st.rerun()

# --- 5. MAIN CHAT INTERFACE ---
st.title("📑 3GPP Packet Core Expert")
st.caption(f"Connected to {selected_model} via {OLLAMA_URL}")

query = st.chat_input("Ask about 5G Call Flows, 5QI, or Protocol details...")

if query:
    # Initialize Embedding Model
    embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
    
    # Initialize LLM
    llm = OllamaLLM(
        model=selected_model, 
        base_url=OLLAMA_URL, 
        num_ctx=8192, 
        temperature=0.1
    )
    
    # Load Database
    db = get_db(CHROMA_PATH, _embedding_fn=embeddings)

    if db is None:
        st.error("Vector database not found. Please run 'Re-Ingest' from the sidebar first.")
    else:
        with st.status("Brainstorming response..."):
            # STAGE 1: RETRIEVAL
            start_search = time.perf_counter()
            with S_LATENCY.time():
                results = db.similarity_search(query, k=15)
            search_time = time.perf_counter() - start_search

            # STAGE 2: GENERATION
            context_text = "\n\n---\n\n".join([doc.page_content for doc in results])
            
            template = """
            ### [SYSTEM INSTRUCTION]
            You are an 3GPP expert Packet Core Engineer. Use the provided context to explain technical parameters.
            Synthesize information into a technical flow. Do not be brief.
            
            ### [CONTEXT]
            {context}
            
            ### [USER QUESTION]
            {question}
            
            ### [RESPONSE]
            """
            prompt = template.format(context=context_text, question=query)

            start_gen = time.perf_counter()
            with G_LATENCY.time():
                response = llm.invoke(prompt)
            gen_time = time.perf_counter() - start_gen

        # Display Response
        st.chat_message("assistant").write(response)
        
        # Metadata / Latency Info for User (External)
        with st.expander("Technical Latency Report"):
            cols = st.columns(3)
            cols[0].metric("Search Time", f"{search_time:.3f}s")
            cols[1].metric("Generation Time", f"{gen_time:.3f}s")
            cols[2].metric("Total Latency", f"{(search_time + gen_time):.3f}s")
            
            st.markdown("**Sources used:**")
            sources = list(set([doc.metadata.get('source') for doc in results]))
            for s in sources:
                st.write(f"- {os.path.basename(s)}")
