import os
import openai


client = openai.Client(base_url="http://localhost:1234/v1")

completion = client.chat.completions.create(
    model="local-model",
    max_tokens=2000,  # this field is currently unused
    messages=[
        {
            "role": "system",
            "content": "Always answer in strict Html Formatted Headers, titles, text, and divs.",
        },
        {
            "role": "user",
            "content": "What is Python?, reply in strict Html Formatted Headers, titles, text, and divs.",
        },
    ],
)

print(completion.choices[0].message.content)
