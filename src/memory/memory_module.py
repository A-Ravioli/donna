from langchain.memory import ConversationBufferMemory


def get_memory():
    # Return a simple conversation memory to store chat history.
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    return memory 