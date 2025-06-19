from azur_llm_pool import (AzurePoolLLM)
import logging

# Set the logging level for httpx to WARNING or higher to suppress info and debug messages
logging.getLogger('httpx').setLevel(logging.WARNING)

class AzureLLMFacade:
    """
    A facade for the AzurePoolLLM class, providing a simplified interface for interacting
    with Azure's language model services.

    Usage:
        1. Initialize the facade with desired configurations.
        2. Call the `ask_question` method with your question.

    Example:
        facade = AzureLLMFacade(stream=False, max_tokens_model=8384, max_concurrent_requests=20)
        answer = facade.ask_question("What is the meaning of life?")
        print(answer)
    """

    def __init__(self, stream=False, max_tokens_model=8384, max_concurrent_requests=20):
        """
        Initializes the AzureLLMFacade with the given configurations.

        :param stream: Boolean indicating whether to stream responses.
        :param max_tokens_model: Maximum number of tokens for the model.
        :param max_concurrent_requests: Maximum number of concurrent requests.
        """
        self.azure_pool_llm = AzurePoolLLM(stream, max_tokens_model, max_concurrent_requests)

    def ask_question(self, question, max_tokens=None, temperature=0.00):
        """
        Asks a question to the Azure language model and returns the response.

        :param question: The question to ask.
        :param max_tokens: Optional; maximum number of tokens in the response.
        :param temperature: Optional; temperature setting for the language model.
        :return: The response from the language model.
        """
        messages = [{"role": "user", "content": question}]
        return self.azure_pool_llm.call_llm(messages, max_tokens, temperature)

    def ask_detailed_questions(self, question, depth, max_depth):
        if depth > max_depth:
            return ""

        response = self.ask_question(question)
        subpoints = response.split('\n')

        detailed_content = ""
        for i, subpoint in enumerate(subpoints, start=1):
            if subpoint.strip():
                formatted_subpoint = f"{depth}.{i} {subpoint}"
                subquestion = f"Explain '{subpoint}' in more detail, and output markdown styled responses."
                subresponse = self.ask_detailed_questions(subquestion, depth + 1, max_depth)
                detailed_content += f"### {formatted_subpoint}\n{subresponse}\n\n"

        return detailed_content


def main():
    facade = AzureLLMFacade(stream=False, max_tokens_model=8384, max_concurrent_requests=20)
    course_context = "Odoo 16 Advanced, Modules, Widgets, Owl, and QWeb programming ."
    initial_question = f"Write a detailed course plan on {course_context} in markdown bullet points."
    course_plan = facade.ask_question(initial_question)

    course_points = course_plan.split('\n')
    markdown_output = f"# {course_context}\n\n"
    markdown_output += f"## Course Plan\n\n"

    max_depth = 1  # Adjusted to 3 for three levels of recursion

    for point in course_points:
        if point.strip():
            point_question = f"Explain '{point}' as part  of the course: {course_context}, and output markdown styled responses."
            detailed_content = facade.ask_detailed_questions(point_question, 1, max_depth)
            markdown_output += f"{detailed_content}\n"
            print(f"Point: {point}\n\n{detailed_content}\n\n")

    with open(f"Course_Plan_{course_context}.md", "w") as file:
        file.write(markdown_output)

if __name__ == "__main__":
    main()