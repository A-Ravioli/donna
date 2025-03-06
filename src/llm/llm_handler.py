from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from memory.memory_module import get_memory


def create_conversation_chain(model_name="gpt-3.5-turbo", temperature=0):
    # Create a LangChain chat model with memory to easily swap out LLMs.
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    memory = get_memory()
    conversation = ConversationChain(llm=llm, memory=memory)
    return conversation


def generate_response(conversation_chain, input_text):
    # Use the conversation chain with memory to generate a response.
    return conversation_chain.run(input_text) 