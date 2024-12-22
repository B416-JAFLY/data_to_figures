import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    temperature=0,
    system="你是一位世界级诗人。只能用简短的诗歌回答。",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "为什么海水是咸的？"
                }
            ]
        }
    ]
)
print(message)
print(message.content)
print(message.content[0].text)
