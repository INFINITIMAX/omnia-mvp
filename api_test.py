from dotenv import load_dotenv
import os
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

raspuns = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=200,
    messages=[
        {"role": "user", "content": "Salut! Confirma ca functionezi, intr-o singura propozitie."}
    ]
)

print(raspuns.content[0].text)
