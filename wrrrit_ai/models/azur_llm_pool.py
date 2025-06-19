import logging
import time
from threading import Semaphore

import tiktoken
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)


class AzurePoolLLM:
    def __init__(self, stream=False, max_tokens_model=4000, max_concurrent_requests=20):
        self.stream = stream
        self.max_tokens_model = max_tokens_model
        self.semaphore = Semaphore(max_concurrent_requests)
        self.llm_instances = self._create_llm_instances()

    def _create_llm_instances(self):
        # Initialize server configurations
        server_configs = [
            {
                "deployment_name": "frynol-gpt-3-5",
                "api_key": "29e0f2a85a6d48e2b7819f1badc84a45",
                "api_type": "azure",
                "azure_endpoint": "https://frynol-us.openai.azure.com/openai/deployments/frynol-gpt-3-5",
                "api_version": "2023-08-01-preview",
                "model_kwargs": {},
                "number_of_instances": 10,  # This can be omitted and will default to 1
            },
            {
                "deployment_name": "frynol-gpt-3-5",
                "api_version": "2023-08-01-preview",
                "azure_endpoint": "https://frynol-fr.openai.azure.com/openai/deployments/frynol-gpt-3-5",
                "api_key": "26359669c6df4d99b05328f446f32d8f",
                "api_type": "azure",
                "model_kwargs": {},
                "number_of_instances": 10,  # This can be omitted and will default to 1
            }
            # More configurations can be added here
        ]
        # Create a list to hold the AzureChatOpenAI instances
        llm_instances = []

        # Create a list to hold the AzureChatOpenAI instances
        max_instances = max(
            server.get("number_of_instances", 1) for server in server_configs
        )

        for _ in range(max_instances):
            for server in server_configs:
                # Check if the current server should add another instance in this round
                if server.get("number_of_instances", 1) > 0:
                    llm = AzureChatOpenAI(
                        # deployment_name=server["deployment_name"],
                        streaming=self.stream,
                        api_version=server["api_version"],
                        base_url=server["azure_endpoint"],
                        api_key=server["api_key"],
                        model_kwargs=server["model_kwargs"],
                        callbacks=[StreamingStdOutCallbackHandler()]
                        if self.stream
                        else [],
                    )
                    llm_instances.append(llm)

                    # Decrement the number of instances left to add for this server
                    server["number_of_instances"] -= 1

        return llm_instances

    def get_next_llm_instance(self):
        # Round-robin selection of the next AzureChatOpenAI instance
        llm_instance = self.llm_instances.pop(0)
        self.llm_instances.append(llm_instance)

        return llm_instance

    def _build_prompt(self, messages):
        langchain_messages = []
        for message in messages:
            message_class = {
                "system": SystemMessage,
                "user": HumanMessage,
                "ai": AIMessage,
            }.get(message["role"], SystemMessage)
            langchain_messages.append(message_class(content=message["content"]))
        return ChatPromptTemplate(messages=langchain_messages).format_messages()

    def call_llm(self, messages, max_tokens=None, temperature=0.00):
        self.semaphore.acquire()
        try:
            max_tokens = max_tokens or self.max_tokens_model
            prompt = self._build_prompt(messages)
            llm = self.get_next_llm_instance()

            start_time = time.time()

            response = llm(prompt, max_tokens=max_tokens, temperature=temperature)

            end_time = time.time()
            num_tokens = self.num_tokens_from_string(response.content, "cl100k_base")
            log_message = (
                f"\n\nLLM Pool call completed in {end_time - start_time:.2f} seconds:\n"
                f"{len(response.content.split())} Words... \n"
                f"{num_tokens} Tokens. \n"
                f"{len(response.content)} characters.\n"
                f"Words per second: {len(response.content.split()) / (end_time - start_time):.2f}.\n"
                f"Tokens per second: {num_tokens / (end_time - start_time):.3f}.\n"
                f"LLL BASE EP: {llm.openai_api_base}\n\n"
                # f"response: {response.content}\n\n"
            )

            # Log the consolidated message
            if self.stream:
                logging.info(log_message)

            return response.content
        except Exception as e:
            logging.error(f"An Unexpected error occurred: {e}")
            return None
        finally:
            self.semaphore.release()

    def num_tokens_from_string(self, string: str, encoding_name: str) -> int:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens


# poolAzureLLM = AzurePoolLLM(stream=False)
# messages = [
#     {"role": "system", "content": "Hello, how are you?"},
#     {"role": "user", "content": "What is the meaning of life?"}
# ]
# poolAzureLLM.call_llm(messages)
