from datetime import datetime
from typing import List, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_community.document_loaders import TextLoader, CSVLoader, JSONLoader, PyPDFLoader, UnstructuredWordDocumentLoader

from app.core.logging import logger
from app.models.document import DocumentStatus, Document
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService


async def update_document_status(
        document_id: int,
        status: str = None,
        error_message: str = None,
        chunk_count: int = None,
        vector_id: str = None,
        celery_task_id: str = None,
        db: AsyncSession = None
):
    """更新文档状态"""
    values = {}
    if status is not None:
        values["status"] = status
    if chunk_count is not None:
        values["chunk_count"] = chunk_count
    if vector_id is not None:
        values["vector_id"] = vector_id
    if error_message is not None:
        values["error_message"] = error_message
    if celery_task_id is not None:
        values["celery_task_id"] = celery_task_id
    if status in [DocumentStatus.COMPLETED, DocumentStatus.FAILED]:
        values["processed_at"] = func.now()

    stmt = update(Document).where(Document.id == document_id).values(**values)
    await db.execute(stmt)
    await db.commit()


async def load_document(file_path: str, file_type: str) -> List[Any]:
    """加载文档"""
    loader_map = {
        "txt": TextLoader,
        "csv": CSVLoader,
        "json": JSONLoader,
        "pdf": PyPDFLoader,
        "docx": UnstructuredWordDocumentLoader,
        "doc": UnstructuredWordDocumentLoader,
    }
    loader_class = loader_map.get(file_type.lower())
    if not loader_class:
        raise ValueError(f"不支持的文件类型: {file_type}")
    # 特殊处理 JSONLoader
    if file_type.lower() == "json":
        loader = loader_class(
            file_path=file_path,
            jq_schema=".",  # 提取所有字段
            text_content=False  # 保持原始 JSON 结构，将提取的数据转换为JSON字符串存入page_content字段中
        )
    else:
        loader = loader_class(file_path=file_path)
    return loader.load()


async def process_document_async(document_id: int, file_path: str, file_type: str, user_id: int, task_id: str, db: AsyncSession):
    """异步处理文档"""

    # 1.更新文档状态为处理中
    await update_document_status(document_id, DocumentStatus.PROCESSING, db=db)
    logger.info(f"文档状态更新成功: document_id={document_id}, 状态={DocumentStatus.PROCESSING}")

    # 2. 加载文档
    documents = await load_document(file_path, file_type)
    logger.info(f"文档加载成功: document_id={document_id}, 文件类型={file_type}, 文件路径={file_path}")

    # 3. 拆分文档
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=220,
        chunk_overlap=80,
        separators=[
            "\n==============================\n",
            "\n\n",
            "\n",
            "。",
            "，",
            " ",
            ""
        ]
    )
    chunks = splitter.split_documents(documents)
    logger.info(f"文档拆分成功: document_id={document_id}, 块数={len(chunks)}")

    # 4. 向量化并存入 Milvus
    vector_service = VectorService()
    llm_service = LLMService()
    embedding_model = llm_service.get_embedding_model()

    # 提取文本内容
    texts = [chunk.page_content for chunk in chunks]

    # 获取元数据
    metadata_list = []
    for chunk in chunks:
        metadata = chunk.metadata.copy() if chunk.metadata else {}
        metadata.update({
            "doc_id": document_id,
            "user_id": user_id,
            "file_type": file_type,
            "file_path": file_path
        })
        metadata_list.append(metadata)

    # 生成向量
    embeddings = embedding_model.embed_documents(texts)
    logger.info(f"文档向量化成功: document_id={document_id}, 向量数量={len(embeddings)}")

    # 存入 Milvus
    vector_id = f"doc_{document_id}_{task_id[:8]}"
    insert_result = vector_service.insert_vectors(
        vectors=embeddings,
        texts=texts,
        metadata=metadata_list,
        doc_id=vector_id
    )
    logger.info(f"向量存储成功: document_id={document_id}, vector_id={vector_id}")

    # 5. 更新数据库状态为已完成
    await update_document_status(
        document_id,
        DocumentStatus.COMPLETED,
        chunk_count=len(chunks),
        vector_id=vector_id,
        celery_task_id=task_id,
        db=db
    )

    logger.info(f"文档处理完成: document_id={document_id}, chunks={len(chunks)}")
    return {"document_id": document_id, "chunk_count": len(chunks), "status": "completed"}

