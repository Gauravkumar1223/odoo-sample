import os
import time
import logging

from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import (
    ChatPromptTemplate,
)
from langchain.schema import AIMessage, HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(level=logging.INFO)


class AzureLLM:
    def __init__(
        self,
        stream=False,
        max_tokens_model=8384,
    ):
        # Set environment variables for Azure OpenAI
        api_key = os.getenv("OPENAI_API_KEY2", "29e0f2a85a6d48e2b7819f1badc84a45")

        api_base = os.getenv("OPENAI_API_BASE2", "https://frynol-us.openai.azure.com/")
        api_version = os.getenv("OPENAI_API_VERSION", "2023-08-01-preview")
        api_type = os.getenv("OPENAI_API_TYPE", "azure")
        deployment_name = os.getenv("OPENAI_DEPLOYMENT_NAME", "frynol-gpt-3-5")

        # Assigning to environment variables (not recommended for sensitive keys)
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_BASE"] = api_base
        os.environ["OPENAI_API_VERSION"] = api_version
        os.environ["OPENAI_API_TYPE"] = api_type
        os.environ["OPENAI_DEPLOYMENT_NAME"] = deployment_name

        # Initialize the AzureChatOpenAI
        self.llm = AzureChatOpenAI(
            deployment_name=deployment_name,
            streaming=stream,
            callbacks=[StreamingStdOutCallbackHandler()] if stream else [],
        )
        self.max_tokens_model = max_tokens_model

    def _build_prompt(self, messages):
        langchain_messages = []

        for message in messages:
            if message["role"] == "system":
                langchain_messages.append(SystemMessage(content=message["content"]))
            elif message["role"] == "user":
                langchain_messages.append(HumanMessage(content=message["content"]))
            elif message["role"] == "ai":
                langchain_messages.append(AIMessage(content=message["content"]))

        chat_prompt_template = ChatPromptTemplate(messages=langchain_messages)

        return chat_prompt_template.format_messages()

    def call_llm(self, messages, max_tokens=8192, temperature=0.01):
        start_time = time.time()
        max_tokens = max_tokens or self.max_tokens_model
        if max_tokens <= 0:
            logging.error("Max tokens must be positive.")
            return None

        prompt = self._build_prompt(messages)

        try:
            response = self.llm(prompt)
            end_time = time.time()
            logging.info(f"LLM call completed in {end_time - start_time:.2f} seconds.")
            logging.info(f"LLM call returned {len(response.content.split())} words.")
            return response.content
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None
