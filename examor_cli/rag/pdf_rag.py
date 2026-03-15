"""PDF-based RAG utilities for Examor CLI."""

import os

from rich.console import Console
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

console = Console()


class PDFRAG:
    def __init__(self):
        self.kb_dir = "./knowledge_base/"
        self.vector_db_dir = "./vector_db/"
        os.makedirs(self.kb_dir, exist_ok=True)
        os.makedirs(self.vector_db_dir, exist_ok=True)

        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def load_pdf(self, pdf_path):
        """加载 PDF 并提取文本"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在：{pdf_path}")

        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        console.print(f"✅ PDF 加载完成：共 {len(documents)} 页")
        return documents

    def split_text(self, documents):
        """分割文本为 Chunk（向量化前处理）"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        console.print(f"✅ 文本分割完成：共 {len(chunks)} 个文本块")
        return chunks

    def build_vector_db(self, chunks, save_name="pdf_knowledge"):
        """构建 FAISS 向量数据库并保存"""
        vector_db = FAISS.from_documents(chunks, self.embeddings)
        save_path = f"{self.vector_db_dir}/{save_name}"
        vector_db.save_local(save_path)
        console.print(f"✅ 向量库已保存到：{save_path}")
        return vector_db

    def load_vector_db(self, save_name="pdf_knowledge"):
        """加载向量库（如果已存在）"""
        save_path = f"{self.vector_db_dir}/{save_name}"
        if not os.path.exists(save_path):
            raise Exception("向量库不存在，请先构建：run build-vector-db")

        vector_db = FAISS.load_local(
            save_path,
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        return vector_db

    def retrieve(self, query, k=3):
        """RAG 检索：返回相关上下文"""
        vector_db = self.load_vector_db()
        docs = vector_db.similarity_search(query, k=k)
        context = "\n".join([doc.page_content for doc in docs])
        console.print("[green]✅ RAG 检索完成[/green]")
        return context


__all__ = [
    "PDFRAG",
]

