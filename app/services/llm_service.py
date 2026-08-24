from langchain.agents import create_agent
from langchain.agents.middleware import before_model
from langchain.chat_models import init_chat_model
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.system_prompt import RAG_SYSTEM_PROMPT
from app.services.agent_middleware import handle_history


class LLMService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ALIYUN_API_KEY
        self.base_url = settings.ALIYUN_BASE_URL
        self.model_name = settings.ALIYUN_MODEL

    def get_model(self):
        """初始化模型信息"""
        model = init_chat_model(
            model=self.model_name,
            model_provider='openai',
            api_key=self.api_key,
            base_url=self.base_url,
        )
        return model

    def get_embedding_model(self):
        """初始化嵌入模型"""
        embedding_model = DashScopeEmbeddings(
            model=settings.ALIYUN_EMBEDDING_MODEL,  # 可指定模型，默认是 text-embedding-v1
            dashscope_api_key=self.api_key
        )
        return embedding_model

    def create_agent_with_middleware(self, tools: list = None):
        """创建带中间件的Agent"""
        model = self.get_model()

        # # 历史消息处理中间件
        # @before_model
        # def handle_history(state, runtime):
        #     """
        #     处理历史消息，优化token使用，太多无用的历史消息影响大模型，增加大模型返回的准确率
        #     :param state:
        #     :param runtime:
        #     :return:
        #     """
        #     messages = state.get("messages", [])
        #     if len(messages) > 20:
        #         system_messages = [message for message in messages if isinstance(message, SystemMessage)]
        #         recent_messages = messages[-20:]
        #         state["messages"] = system_messages + recent_messages
        #     return state

        agent = create_agent(
            model=model,
            system_prompt=RAG_SYSTEM_PROMPT,
            tools=tools or [],
            middleware=[handle_history]
        )

        return agent

    async def stream_agent_response(self, query: str, thread_id: str, tools: list = None):
        """流式调用agent， 使用sse推送"""
        agent = self.create_agent_with_middleware(tools)
        async for chunk in agent.astream(
                {'messages': [HumanMessage(content=query)]},
                stream_mode='messages',
                config={"configurable": {"thread_id": thread_id}}
        ):
            yield chunk

