import streamlit as st
import os, time, shutil
from prometheus_client import Summary, start_http_server
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

# Start Metrics Server on Port 8000
try:
    start_http_server(8000)
except:
    pass 

S_LATENCY = Summary('search_latency_seconds', 'Time spent in vector search')
G_LATENCY = Summary('gen_latency_seconds', 'Time spent in LLM generation')

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DATA_PATH = os.getenv("PDF_DATA_PATH", "/app/data")
CHROMA_PATH = "/app/chroma_db"

st.set_page_config(page_title="3GPP AI Assistant", layout="wide")

# Leading underscore _embedding_fn stops the UnhashableParamError
@st.cache_resource
def get_db(path, _embedding_fn):
    if os.path.exists(path):
        return Chroma(persist_directory=path, embedding_function=_embedding_fn)
    return None

with st.sidebar:
    st.title("⚙️ Engineering Console")
    selected_model = st.selectbox("Select LLM Model", ["llama3.2", "gemma3:4b"])
    if st.button("🔄 Re-Ingest 3GPP PDFs"):
        with st.status("Indexing..."):
            if os.path.exists(CHROMA_PATH): shutil.rmtree(CHROMA_PATH)
            loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PyPDFLoader)
            docs = loader.load()
            splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
            chunks = splitter.split_documents(docs)
            embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
            Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
            st.success("Ingestion Complete!")
            st.rerun()

st.title("📑 3GPP Packet Core Expert")
query = st.chat_input("Ask about 5G/EPC Specs...")

if query:
    embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_URL)
    llm = OllamaLLM(model=selected_model, base_url=OLLAMA_URL, num_ctx=8192, temperature=0.1)
    db = get_db(CHROMA_PATH, _embedding_fn=embeddings)

    if db:
        with st.status("Analyzing..."):
            with S_LATENCY.time():
                results = db.similarity_search(query, k=10)
            
            context = "\n\n".join([d.page_content for d in results])
            prompt = f"Context: {context}\n\nQuestion: {query}\n\nDetailed Technical Answer:"
            
            with G_LATENCY.time():
                response = llm.invoke(prompt)

        st.chat_message("assistant").write(response)
        st.info(f"Latency: Search {S_LATENCY.collect()[0].samples[0].value:.2f}s | Gen {G_LATENCY.collect()[0].samples[0].value:.2f}s")
