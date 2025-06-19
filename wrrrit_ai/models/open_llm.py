import openai
import os
import logging

import time


# Configure global logging settings
# logging.basicConfig(level=logging.INFO)

# Create a global logger
_logger = logging.getLogger(__name__)

# Define global variables
API_BASE = "https://4dazyw3bz4bp30-8000.proxy.runpod.net/v1"

# "https://api.openai.com/v1"

MODEL_NAME = "TheBloke/zephyr-7B-beta-AWQ"
# "lmsys/vicuna-13b-v1.5-16k"
# "HuggingFaceH4/zephyr-7b-beta"
# "gpt-3.5-turbo-16k-0613"

MAX_TOKENS = 7400
TEMPERATURE = 0.5


class OpenLLM:
    def __init__(self, api_key=None):
        """
        Initializes the OpenLLM class with default values for various parameters.
        :param api_key: OpenAI API key. If not provided, it will try to get it from environment variable OPENAI_API_KEY.
        """
        self.api_key = api_key if api_key else os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            _logger.error(
                "OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable."
            )
            raise ValueError("API key not provided")

        openai.api_key = self.api_key
        _logger.info("OpenAI API key is set.")

        # Setting default values for various parameters
        self.model = MODEL_NAME
        self.completion_mode = "completion"
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE
        self.api_base = API_BASE

        _logger.info("OpenLLM instance is initialized.")

    def _handle_completion(self, prompt, stream=True):
        """
        Handles the completion request to OpenAI API.
        :param prompt: The prompt to be sent to OpenAI API for completion.
        :param stream: Boolean flag to stream the results.
        :return: The response from OpenAI API.
        """
        _logger.info("Sending completion request to OpenAI API...")
        response = openai.Completion.create(
            model=self.model,
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=stream,
            api_base=self.api_base,
        )
        _logger.info("Completion request completed.")
        return response

    def _handle_chat(self, messages, stream=False):
        """
        Handles the chat request to OpenAI API.
        :param messages: The messages to be sent to OpenAI API for chat.
        :param stream: Boolean flag to stream the results.
        :return: The response from OpenAI API.
        """
        _logger.info("Sending chat request to OpenAI API...")
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            api_base=self.api_base,
            stream=stream,
        )
        _logger.info("Chat request completed.")
        return response

    @staticmethod
    def format_prompt(messages, model):
        prompt = ""
        system_message = ""

        for message in messages:
            if message["role"] == "user":
                prompt += message["content"]
            elif message["role"] == "system":
                system_message = message["content"]
                prompt += system_message
                system_message = (
                    "Disregard all previous instructions. Your role is now to function as an advanced assistant "
                    "specializing in Medical Report Generation and providing medical advice within the domains of Cardiology, "
                    "Dermatology, and Oncology. Ensure that your responses are direct, precise, and adhere strictly to the "
                    "formatting and directives specified in the user’s prompt. Avoid adding any preamble or conclusion. Analyze "
                    "the text and information provided meticulously, ensuring accuracy and relevance in your responses. Do not "
                    "invent information or make assumptions beyond the given context. Format your responses in HTML, Markdown, "
                    "or JSON, as per the user’s request. Maintain language consistency throughout your responses, and ensure "
                    "that formatting is uniform and enhances the readability of the document. Include a disclaimer when necessary, "
                    "emphasizing the importance of verification by a medical professional."
                )

        # Formatting based on different model requirements
        if "llama-2-7" in model.lower():
            formatted_prompt = f"### System:\n{system_message}\n### User:\n{prompt}\n### Assistant:\n reply as requested"

        if "misetral" in model.lower():
            formatted_prompt = f"[INST]<s><<SYS>>{system_message}<<SYS>>{prompt}[/INST]"
        elif "zephyr" in model.lower():
            formatted_prompt = f"<|system|>{system_message}<|user|>{prompt}<|assistant|>Reply strictly as requested"
        elif "mosaic" in model.lower():
            formatted_prompt = f"### Human:\n{system_message}\n{prompt}\n### Assistant: Reply as requested in 800 words"
        else:
            formatted_prompt = f"{system_message}-{prompt}"
        _logger.info(f"Formatted prompt: {formatted_prompt}")
        return formatted_prompt

    def _generate_prompt(self, messages):
        """
        Generates a prompt from messages for completion mode.
        :param messages: A list of message dicts with 'role' and 'content' keys.
        :return: A string prompt.
        """
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            prompt += f" {content}"
        return prompt

    def call_llm(self, messages, stream=True):
        """
        Calls the LLM based on the specified parameters.
        :param messages: A list of message dicts with 'role' and 'content' keys.
        :param stream: Boolean flag to stream the results. Default is False.
        :return: The response content from LLM.
        """
        _logger.info("Starting LLM call...")
        start_time = time.time()  # Start timing
        try:
            if self.completion_mode == "chat":
                response = self._handle_chat(messages, stream=stream)
            else:
                prompt = self.format_prompt(messages, self.model)
                response = self._handle_completion(prompt, stream=stream)

            if stream:
                full_response = ""
                for chunk in response:
                    content = (
                        chunk["choices"][0].get("text", "")
                        if self.completion_mode == "completion"
                        else chunk["choices"][0].get("delta", {}).get("content", "")
                    )
                    if content:
                        print(content, end="")
                        full_response += content
                end_time = time.time()  # End timing
                duration = end_time - start_time
                word_count = len(full_response.split())
                words_per_second = word_count / duration if duration > 0 else 0
                _logger.info(
                    f"LLM call completed in {duration:.2f} seconds. Generated {word_count} words. Words per second: {words_per_second:.2f}"
                )
                return full_response
            else:
                content = (
                    response["choices"][0].get("text", "")
                    if self.completion_mode == "completion"
                    else response["choices"][0]["message"]["content"]
                )
                end_time = time.time()  # End timing
                duration = end_time - start_time
                word_count = len(content.split())
                words_per_second = word_count / duration if duration > 0 else 0
                _logger.info(
                    f"LLM call completed in {duration:.2f} seconds. Generated {word_count} words. Words per second: {words_per_second:.2f}"
                )
                return content
        except Exception as e:
            _logger.error(f"An error occurred: {e}")
            return None


# Number of threads
# num_threads = 1

# Using ThreadPoolExecutor to run the function in parallel threads
# with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
#     # Starting threads for OpenAI model and waiting for their results
#     results_openai = list(executor.map(run_thread_openai, range(num_threads)))
#
# # Display results for OpenAI model
# for i, (time_taken, num_words, response) in enumerate(results_openai, start=1):
#     logging.info(f"OpenAI Model - Thread {i}: Time taken = {time_taken:.2f} seconds, Number of words in response = {num_words}, Words per second = {num_words/time_taken:.2f}")

# Using ThreadPoolExecutor to run the function in parallel threads for opensource models
# with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
#     # Starting threads for opensource model and waiting for their results
#     results_opensource = list(executor.map(run_thread_opensource, range(num_threads)))
#
# # Display results for opensource model
# for i, (time_taken, num_words, response) in enumerate(results_opensource, start=1):
#     logging.info(f"OpenSource Model - Thread {i}: Time taken = {time_taken:.2f} seconds, Number of words in response = {num_words}, Words per second = {num_words/time_taken:.2f}")
# llm = OpenLLM()
# system_test = """Ensure a detailed, thorough, and expansive response, maintaining a minimum word count of 13000 words and replying solely in HTML formatted text for all components of the response. When generating histories on topics or civilizations, use "<h1>Title Level 1</h1>", "<h2>Title Level 2</h2>", and "<h3>Title Level 3</h3>" for headings. All historical information must be accurate, factual, and presented in a structured HTML format. Avoid including any introductory text, concluding remarks, or commentary not directly related to the topic at hand. This directive is to remain in effect until a different instruction is provided.
# """
# user_test = """Deliver a comprehensive and meticulously detailed history of Tunisia, spanning from its inception to present practices, ensuring a response length of a minimum of 3000 words. Structure the content with "<h1>" for main chapters, "<h2>" for sub-chapters, and "<h3>" for sub-sections. Apply a consistent yellow color (#FFFF00) to all main chapter titles, and a consistent gree color (#00FF00) to sub-chapters and sub-sections, aiming to enhance readability and visual appeal. Ensure all historical data, including dates and events, are presented in a clear, coherent, and chronological manner.
#
# Present the information in English, adopting an engaging, attractive writing style to capture the reader's interest and facilitate a deep, immersive learning experience. Maintain simplicity, clarity, and accessibility in language to cater to a diverse audience, including those with no background in medical history. Ensure that the historical information is reliable, supported by evidence, and easy to follow.
#
# Incorporate educational insights, contextual information, and analytical commentary to enhance understanding of historical events and their significance. Provide clear explanations for specialized terms, concepts, and events, ensuring a thorough educational experience for all readers.
#
# """
# messages_test = [
#     {"role": "user", "content": user_test},
#     {"role": "system", "content": system_test},
# ]
# response_test = llm.call_llm(messages_test, stream=True)
