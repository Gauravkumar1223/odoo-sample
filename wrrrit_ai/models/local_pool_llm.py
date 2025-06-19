import logging
import time
from threading import Semaphore

import openai
import tiktoken
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from .timer_decorator import log_execution_time

# Configure logging
logging.basicConfig(level=logging.INFO)


class LocalPoolLLM:
    def __init__(self, stream=False, max_tokens_model=8384, max_concurrent_requests=20):
        self.stream = stream
        self.max_tokens_model = max_tokens_model
        self.semaphore = Semaphore(max_concurrent_requests)
        self.llm_instances = self._create_llm_instances()

    def _create_llm_instances(self):
        # Local LLM server configuration
        local_server_config = {
            "base_url": "http://localhost:1234/v1",
            "number_of_instances": 10,  # Adjust as needed
        }

        # Create a list to hold the LLM instances
        llm_instances = []
        for _ in range(local_server_config["number_of_instances"]):
            llm = openai.Client(base_url=local_server_config["base_url"])
            llm_instances.append(llm)

        return llm_instances

    def _get_next_llm_instance(self):
        # Round-robin selection of the next LLM instance
        llm_instance = self.llm_instances.pop(0)
        self.llm_instances.append(llm_instance)
        return llm_instance

    def _build_prompt(self, messages):
        formatted_messages = []
        for message in messages:
            message_class = {
                "system": SystemMessage,
                "user": HumanMessage,
                "ai": AIMessage,
            }.get(message["role"], SystemMessage)

            # Create message instance
            langchain_message = message_class(content=message["content"])

            # Convert to a format that is JSON serializable
            formatted_message = {
                "role": message["role"],
                "content": langchain_message.content,
            }
            formatted_messages.append(formatted_message)

        return formatted_messages

    def call_llm(self, messages, max_tokens=None, temperature=0.00):
        self.semaphore.acquire()
        try:
            max_tokens = max_tokens or self.max_tokens_model
            langchain_messages = self._build_prompt(messages)
            llm = self._get_next_llm_instance()

            start_time = time.time()

            response = llm.chat.completions.create(
                model="local-model",  # This field can be adjusted as needed
                messages=langchain_messages,
            )

            end_time = time.time()
            response_content = response.choices[0].message.content
            num_tokens = self.num_tokens_from_string(response_content, "cl100k_base")
            log_message = self._format_log_message(
                start_time, end_time, response_content, num_tokens, llm.base_url
            )

            # Log the consolidated message
            logging.info(log_message)
            print(log_message)
            return response_content
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return None
        finally:
            self.semaphore.release()

    @log_execution_time(enable_timer=True)
    def num_tokens_from_string(self, string: str, encoding_name: str) -> int:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def _format_log_message(
        self, start_time, end_time, response_content, num_tokens, base_url
    ):
        # Implement log message formatting here
        return f"Log message: {response_content}, \n tokens: {num_tokens} "


#
# localPoolLLM = LocalPoolLLM(stream=False)
# messages = [
#     {"role": "system", "content": "Hello, how are you?"},
#     {"role": "user", "content": "What is the meaning of life?"},
# ]
# localPoolLLM.call_llm(messages)
