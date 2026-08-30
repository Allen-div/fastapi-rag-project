import os
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import chardet
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentUploadResponse, DocumentListResponse
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.utils.document_utils import update_document_status
from app.utils.utils import decode_file_content
from app.tasks.documents.documents_tasks import process_document

router = APIRouter()

# 允许的文件类型
ALLOWED_FILE_TYPES = {
    "txt": "text/plain",
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "csv": "text/csv",
    "json": "application/json"
}

# 确保静态目录存在
STATIC_DIR = "static/uploads"
os.makedirs(STATIC_DIR, exist_ok=True)

@router.post('/upload', response_model=DocumentUploadResponse)
async def upload_document(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    上传文档 - 立即返回，Celery 后台异步处理
    """
    # 1. 验证文件类型
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(ALLOWED_FILE_TYPES.keys())}"
        )

    # 2. 验证文件大小（限制100MB）
    file_size = 0
    content = await file.read()
    file_size = len(content)

    if file_size > 100 * 1024 * 1024:  # 100MB
        raise HTTPException(
            status_code=400,
            detail="文件大小超过限制（最大100MB）"
        )

    # 3. 生成文件名和路径
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(STATIC_DIR, safe_filename)

    # 4. 保存文件到本地
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 5. 创建文档记录
    document_service = DocumentService(db)
    doc = await document_service.create_document(current_user.id, file.filename, file_path, file_ext, file_size, DocumentStatus.PENDING)

    # 6. 提交 Celery 异步任务（delay 返回 AsyncResult，不可 await；db 不可跨进程序列化，由任务内部自建 session）
    task = process_document.delay(
        document_id=doc.id,
        file_path=file_path,
        file_type=file_ext,
        user_id=current_user.id,
    )

    # 7. 保存 Celery 任务ID到数据库
    await update_document_status(document_id=doc.id, celery_task_id=task.id, db=db)

    # 8. 立即返回成功响应
    return DocumentUploadResponse(
        doc_id=doc.id,
        file_name=file.filename,
        file_size=file_size,
        status="pending",
        task_id=task.id,
        message="文件上传成功，正在后台处理..."
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 10
):
    """列出用户的文档"""
    rag_service = DocumentService(db)
    documents, total = await rag_service.list_user_documents(current_user.id, page, page_size)
    return {
        "documents": documents,
        "total": total
    }


@router.delete("/documents/{document_id}")
async def delete_document(
        document_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """删除文档"""
    service = DocumentService(db)
    await service.delete_document(userid=current_user.id, document_id=document_id)
    return {'msg': '文档删除成功', 'id': document_id}