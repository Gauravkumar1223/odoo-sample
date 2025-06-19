import os
from dotenv import load_dotenv
import logging
import langchain

load_dotenv()
logging.basicConfig(level=logging.INFO)

_logger = logging.getLogger(__name__)


_logger.info("Starting up...")
_logger.info("Environment variables loaded")
_logger.info("List of environment variables:")
for key, value in os.environ.items():
    _logger.info(f"{key}: {value}")

_logger.info("Done!")


from langchain.chat_models import AzureChatOpenAI as ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

chat = ChatOpenAI(deployment_name="frynol-gpt-3-5")
messages = [
    SystemMessage(
        content="You are a helpful assistant that translates English to French."
    ),
    HumanMessage(content="I love programming."),
]
chat(messages)
resp = chat(messages)
_logger.info("Response: %s", resp.content)

from langchain.chains import ConversationChain

conversation = ConversationChain(llm=chat)
resp = conversation.run(
    "Translate this sentence from English to French: I love programming."
)
_logger.info("Response: %s", resp)
resp = conversation.run("Translate it to German.")
_logger.info("Response: %s", resp)
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
memory.chat_memory.add_user_message("hi!")
memory.chat_memory.add_ai_message("whats up?")
memory.load_memory_variables({})
_logger.info("Memory variables: %s", memory.memory_variables)


import os

from langchain.llms import AzureOpenAI
from langchain.output_parsers import XMLOutputParser
from langchain.prompts import PromptTemplate

deployed_model = os.environ.get("OPENAI_DEPLOYEMENT_MODEL_NAME")
