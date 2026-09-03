import os
import uuid
from typing import Dict, List, Tuple, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.document import Document
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService


class RAGService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.vector_service = VectorService()

    def split_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """文本分块"""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunks.append(text[start:end])
            start = end - overlap if end < text_length else text_length

        return chunks

    async def process_document(self, user_id: str, file_name: str, content: str) -> Dict:
        """处理文档，分块并向量化"""

        # 分块
        chunks = self.split_text(content)

        # 获取嵌入
        embedding_model = self.llm_service.get_embedding_model()
        embeddings = embedding_model.embed_documents(chunks)

        # 生成文档ID
        doc_id = str(uuid.uuid4())

        # 准备元数据
        metadata = [{"user_id": user_id, "file_name": file_name, "chunk_index": i} for i in range(len(chunks))]

        # 存入Milvus
        self.vector_service.insert_vectors(
            vectors=embeddings,
            texts=chunks,
            metadata=metadata,
            doc_id=doc_id
        )

        # 保存到mysql
        doc = Document(
            user_id=user_id,
            file_name=file_name,
            file_path=file_name,
            file_type=file_name.split('.')[-1] if '.' in file_name else 'txt',
            file_size=len(content),
            chunk_count=len(chunks),
            vector_id=doc_id
        )

        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)

        return {
            "doc_id": doc_id,
            "chunk_count": len(chunks)
        }

    async def get_relevant_documents(self, content: str, top_k: int) -> Sequence[Dict]:
        """根据查询文本做混合检索（稠密语义 + BM25 关键词，RRF 融合）"""

        # 获取查询向量（稠密）
        embedding_model = self.llm_service.get_embedding_model()
        query_vector = embedding_model.embed_query(content)
        # print(f"--------查询向量: {query_vector}-----------------------")

        # 混合检索：稠密向量 + BM25 关键词
        results = self.vector_service.hybrid_search(query_vector, content, top_k)
        # print(f"---------混合检索结果：{results}--------------------")

        relevant_docs = []
        if results and len(results) > 0:
            for result in results[0]:
                entity = result.get("entity", {}) or {}
                relevant_docs.append(
                    {
                        "text": entity.get("text", ""),
                        "score": result.get("distance", 0),
                        "metadata": entity.get("metadata", {}),
                    }
                )
        return relevant_docs
