import multiprocessing

import logging
import time
import random

from azur_llm_pool import (
    AzurePoolLLM,
)  # Replace 'your_module' with the actual module name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def process_task(messages):
    """
    Function to be executed by each process. It initializes the AzurePoolLLM and makes a call to the LLM.
    Logs start time, end time, and duration of the process.
    """
    start_time = time.time()
    logging.info("Starting process %s", multiprocessing.current_process().name)

    poolAzureLLM = AzurePoolLLM(stream=False)
    result = poolAzureLLM.call_llm(messages)

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Process completed. Duration: {duration:.2f} seconds")

    return result


def generate_random_tasks(num_tasks=10):
    roles = ["system", "user", "ai"]
    contents = [
        "Hello, how can I assist you today?",
        "What is the weather like today?",
        "Can you provide me with the latest news?",
        "How do I solve a quadratic equation?",
        "What are some good places to visit in Paris?",
        "Tell me a joke.",
        "What's the meaning of life?",
        "How does blockchain technology work?",
        "Can you recommend a good book to read?",
        "What are the benefits of meditation?",
    ]

    tasks = []
    for _ in range(num_tasks):
        num_messages = random.randint(1, 3)  # Random number of messages per task
        messages = [
            {"role": random.choice(roles), "content": random.choice(contents)}
            for _ in range(num_messages)
        ]
        tasks.append(messages)

    return tasks


def main():
    # Example messages to be processed
    tasks = generate_random_tasks(num_tasks=2)
    # Number of processes
    num_processes = 5
    star_time = time.time()
    # Creating a pool of processes
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Distribute tasks among processes and get results
        results = pool.map(process_task, tasks)
    end_time = time.time()
    # Handling the results
    for result in results:
        print(result)
    process_duration = end_time - star_time
    print(f"Total duration: {process_duration:.2f} seconds")


if __name__ == "__main__":
    main()
