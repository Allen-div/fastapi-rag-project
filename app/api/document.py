from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import chardet
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.document import DocumentUploadResponse, DocumentListResponse
from app.services.rag_service import RAGService
from app.utils.utils import decode_file_content

router = APIRouter()


@router.post('/upload', response_model=DocumentUploadResponse)
async def upload_document(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """上传文档并向量化"""
    rag_service = RAGService(db)

    # 读取文件
    content = await file.read()
    # text = content.decode('utf-8')

    # 2. 检查文件是否为空
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 3. 解码文件内容
    try:
        text = decode_file_content(content)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"文件解码失败: {str(e)}"
        )

    # 4. 检查解码后的文本是否为空
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空或无法解析")

    # 处理文档
    from app.main import logger
    logger.info(f"--------{len(text)}---{text[:6]}-------")
    result = await rag_service.process_document(
        user_id=current_user.id,
        file_name=file.filename,
        content=text
    )

    return DocumentUploadResponse(
        doc_id=result["doc_id"],
        file_name=file.filename,
        chunk_count=result["chunk_count"],
        status="success"
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 10
):
    """列出用户的文档"""
    rag_service = RAGService(db)
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
    service = RAGService(db)
    await service.delete_document(userid=current_user.id, document_id=document_id)
    return {'msg': '文档删除成功', 'id': document_id}