import openai, os
import logging

from .bg_generic_runner import run_in_background

# Configure logging
logging.basicConfig(level=logging.INFO)


class WrrritLLM:
    def __init__(
        self,
        model_type="openai-gpt",
        model_chat="gpt-3.5-turbo-16k-0613",
        model_completion="gpt-3.5-turbo-instruct",
        api_base="https://api.openai.com/v1",
        max_tokens_model=8384,
        api_key=None,
    ):
        self.config = {
            "model_type": model_type,
            "model_chat": model_chat,
            "model_completion": model_completion,
            "api_base": api_base,
            "max_tokens_model": max_tokens_model,
        }
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    SYSTEM_PROMPT = """<s>[INST] <<SYS>
    You are helpful. Your answers are clear and concise.
    You start responding directly to the request, without pre-amble.
    You reply following the mentioned instructions.
    </SYS>>
    """

    def format_prompt(self, message):
        if self.config["model_type"] == "openai-llama":
            return self.format_prompt_for_llama(message)
        # Add other conditions for different model types if needed
        return message

    @staticmethod
    def format_prompt_for_llama(message):
        """
        Formats the message for the Llama model.

        Parameters:
            message (str): Current message to send.

        Returns:
            str: Formatted message string
        """
        formatted_message = WrrritLLM.SYSTEM_PROMPT + f"{message} [/INST]"
        return formatted_message

    def handle_completion(self, prompt, remaining_tokens, temperature, stream):
        response = openai.Completion.create(
            model=self.config["model-completion"],
            api_base=self.config["api_base"],
            max_tokens=remaining_tokens,
            temperature=temperature,
            prompt=prompt,
            stream=stream,
        )
        return response

    def handle_chat(self, messages, remaining_tokens, temperature, stream):
        response = openai.ChatCompletion.create(
            model=self.config["model_chat"],
            api_base=self.config["api_base"],
            max_tokens=remaining_tokens,
            temperature=temperature,
            messages=messages,
            stream=stream,
        )
        return response

    def calculate_remaining_tokens(self, messages, max_tokens):
        message_length_in_tokens = sum(
            [len(message["content"].split()) for message in messages]
        )
        logging.info(f"Messages length in tokens: {message_length_in_tokens}")
        return max_tokens - message_length_in_tokens

    def transform_messages_to_prompt(self, messages):
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            prompt += f"{role}: {content}\n"
        return self.format_prompt(
            prompt
        )  # Use the format_prompt method to handle different model types

    def call_llm(
        self,
        messages,
        max_tokens=8384,
        temperature=0.01,
        completion_mode="chat",
        stream=False,
    ):
        max_tokens = max_tokens or self.config["max_tokens_model"]
        openai.api_key = self.api_key
        logging.info("Starting LLM call with API Key: %s", self.api_key)

        remaining_tokens = self.calculate_remaining_tokens(messages, max_tokens)
        if remaining_tokens <= 0:
            logging.error("Insufficient tokens remaining for the request.")
            return

        full_response = ""
        try:
            if completion_mode == "completion":
                prompt = self.transform_messages_to_prompt(messages)
                prompt = self.format_prompt(
                    prompt
                )  # Format the prompt based on model type
                response = self.handle_completion(
                    prompt, remaining_tokens, temperature, stream
                )
            else:
                response = self.handle_chat(
                    messages, remaining_tokens, temperature, stream
                )

            if stream:
                for chunk in response:
                    content = (
                        chunk["choices"][0].get("text", "")
                        if completion_mode == "completion"
                        else chunk["choices"][0].get("delta", {}).get("content", "")
                    )
                    if content is not None:
                        print(content, end="")
                    full_response += content
            else:
                full_response = (
                    response["choices"][0].get("text", "")
                    if completion_mode == "completion"
                    else response["choices"][0]["message"]["content"]
                )

            return full_response

        except Exception as e:
            logging.error(f"OpenAI error: {e}")

            return None


# Example usage:

# wrrrit_llm = WrrritLLM(
#     model_chat="gpt-3.5-turbo",
#     model_completion="gpt-3.5-turbo-instruct",
#     api_base="http://ultron.local:8000/v1",
#     max_tokens_model=4096,
# )
# messages = [
#     {
#         "role": "user",
#         "content": "be short and Give me a list of 3 programming patterns used in OOP",
#     }
# ]
# response = wrrrit_llm.call_llm(messages, completion_mode="chat", stream=True)
# print(response)
