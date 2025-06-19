import concurrent.futures
import logging
import time
from azur_llm_pool import AzurePoolLLM

logging.basicConfig(level=logging.INFO)

poolAzureLLM = AzurePoolLLM(stream=False)


# Function to call LLM with a specific message
def call_llm_task(message_id):
    start_time = time.time()
    try:
        # Create a new instance of AzurePoolLLM for each process

        messages = [
            {"role": "system", "content": f"You are a helpful AI Assistant"},
            {"role": "user", "content": f"Write a poem for me"},
        ]
        response = poolAzureLLM.call_llm(messages)
        elapsed_time = time.time() - start_time
        logging.info(f"Task {message_id} completed in {elapsed_time:.2f} seconds.")
        return response, elapsed_time
    except Exception as e:
        logging.error(f"Error in call_llm_task {message_id}: {e}")
        return None, time.time() - start_time


if __name__ == "__main__":
    start_time = time.time()
    logging.info("Starting multiprocessing calls to AzurePoolLLM.")

    # Number of parallel calls to make
    num_calls = 10
    logging.info(f"Making {num_calls} parallel calls.")

    # Use ProcessPoolExecutor for multiprocessing
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_calls) as executor:
        # Dispatch call_llm_task for different message IDs
        futures = {executor.submit(call_llm_task, i) for i in range(num_calls)}

        # Process the completed futures
        for future in concurrent.futures.as_completed(futures):
            try:
                response, elapsed_time = future.result()
                if response:
                    logging.info(f"Response received in {elapsed_time:.2f} seconds")
                else:
                    logging.info(
                        f"No response received. Task completed in {elapsed_time:.2f} seconds."
                    )
            except Exception as e:
                logging.error(f"Error processing future: {e}")

    total_elapsed_time = time.time() - start_time
    logging.info(f"All tasks completed in {total_elapsed_time:.2f} seconds.")
