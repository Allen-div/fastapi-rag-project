from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langchain_core.messages import SystemMessage
from langgraph.runtime import Runtime


@before_model
def handle_history(state: AgentState, runtime: Runtime):
    """
    处理历史消息，节省token使用，太多无用的历史消息影响大模型输出
    :param state:
    :param runtime:
    :return:
    """
    messages = state.get("messages", [])
    if len(messages) > 20:
        system_messages = [message for message in messages if isinstance(message, SystemMessage)]
        recent_messages = messages[-20:]
        state["messages"] = system_messages + recent_messages
    return state