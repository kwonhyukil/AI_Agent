from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "안녕! 한 문장으로 자기소개 해줘."}
    ]
)

print(response.content[0].text)
