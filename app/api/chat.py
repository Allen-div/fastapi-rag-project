import json
import time

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, AIMessageChunk, ToolMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ConversationListResponse, ConversationResponse, MessageListResponse
from app.services.chat_history_service import ChatHistoryService, ConversationService, MessageService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """创建新对话"""
    chat_service = ChatHistoryService(db)
    conversation = await chat_service.create_conversation(
        user_id=current_user.id,
        title="新对话"
    )
    return conversation


@router.post("/stream")
async def chat_stream(
        request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """sse流式对话接口"""
    chat_service = ChatHistoryService(db)
    llm_service = LLMService()
    rag_service = RAGService(db)

    # 获取或者创建对话
    if request.thread_id:
        # 如果用户传了相应的thread_id，说明是继续老的聊天
        conversation = await chat_service.get_conversation_by_thread_id(request.thread_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在或无权限访问")

        # 若标题仍是占位符（"新对话"），用第一条消息更新标题
        if conversation and conversation.title == "新对话":
            conversation.title = request.query[:50] + "..."
            await db.commit()
    else:
        # 用户新开聊天
        conversation = await chat_service.create_conversation(
            user_id=current_user.id,
            title=request.query[:50] + "..."
        )
        request.thread_id = conversation.thread_id

    # 获取对话框ID
    conversation_id = await chat_service.get_conversation_id(thread_id=request.thread_id)

    if not request.top_k:
        request.top_k = 5

    # 保存本次用户消息
    await chat_service.add_message(
        conversation_id=conversation_id,
        role='user',
        content=request.query
    )

    # 获取相关文档（RAG）
    query_result = await rag_service.get_relevant_documents(
        request.query,
        request.top_k
    )

    # 构建返回内容
    hit_texts = []
    if query_result:
        for result in query_result:
            text = result.get('text')
            score = result.get('score')
            hit_texts.append(f"片段{text} | 得分: {score}")
    hit_text = '\n'.join(hit_texts)

    user_prompt = f"""

## 参考文档
{hit_text}

## 用户问题
{request.query}

        """

    # 组装历史消息：user -> HumanMessage, assistant -> AIMessage
    # 注意：本次用户消息已在上方 add_message 保存，list_messages 升序取回后最后一条即本轮 user。
    history_messages = await chat_service.list_messages(conversation_id)
    messages = []
    for msg in history_messages:
        if msg.role == 'user':
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == 'assistant':
            messages.append(AIMessage(content=msg.content))
        # tool 等其它角色忽略

    # 将"当前提问"替换为带参考文档的完整 prompt（RAG 片段只在当次注入，不落库）。
    # 正常情况下最后一条就是刚保存的本次用户消息；
    # 若因任何边界情况最后一条不是 HumanMessage，则显式追加，确保当前问题一定进入上下文。
    if messages and isinstance(messages[-1], HumanMessage):
        messages[-1].content = user_prompt
    else:
        messages.append(HumanMessage(content=user_prompt))

    async def generate_sse():
        """sse生成数据"""
        full_response = ''

        # 收集工具调用信息
        tool_calls = []

        async for chunk in llm_service.stream_agent_response(
            messages,
            request.thread_id,
            tools=None
        ):
            # chunk的类型可能为：<class 'langchain_core.messages.ai.AIMessageChunk'>
            # chunk的类型可能为：<class 'langchain_core.messages.tool.ToolMessage'>
            # ToolMessage是工具返回的内容，按理说不用返回给用户，但是这里没有绑定工具，可以忽略
            if type(chunk[0]) == AIMessageChunk:
                chunk_content = chunk[0].content
                full_response += chunk_content

                yield f"data: {json.dumps({'content': chunk_content, 'type': 'ai_content'})}\n\n"
            elif type(chunk[0]) == ToolMessage:
                tool_content = chunk[0].content
                yield f"data: {json.dumps({'content': tool_content, 'type': 'tool_content'})}\n\n"


        # 保存本次助手消息
        await chat_service.add_message(
            conversation_id=conversation_id,
            role='assistant',
            content=full_response
        )

        # 发送完成信号
        yield f"data: {json.dumps({'type': 'done', 'thread_id': request.thread_id})}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get('/conversation', response_model=ConversationListResponse)
async def get_conversations(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        page: int = 1,
        page_size: int = 10
):

    chat_service = ConversationService(db)
    user_id = current_user.id
    conversations, total = await chat_service.get_conversations(user_id, page, page_size)
    return {
        "conversations": conversations,
        "total": total
    }


@router.get('/messages', response_model=MessageListResponse)
async def get_messages(
        conversion_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    t1 = time.time()
    message_service = MessageService(db)
    conversation_service = ConversationService(db)
    conversion = await conversation_service.get_conversation(current_user.id, conversion_id)
    if not conversion:
        return HTTPException(
            status_code=400,
            detail="对话不存在"
        )
    messages, total = await message_service.get_messages(conversion_id)
    print(f"----------{time.time() - t1}---------------")
    return {
        'messages': messages,
        'total': total
    }

