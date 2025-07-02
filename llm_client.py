import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.base_url:
            self.model = os.getenv("MODEL")
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        else:
            self.model = os.getenv("OPENAI_MODEL")
            self.client = OpenAI(api_key=self.api_key)

    def get_client(self):
        return self.client

    def get_model(self):
        return self.model

    def chat_completion(self, messages, response_format=None, **kwargs):
        params = {
            "model": self.model,
            "messages": messages
        }
        if response_format:
            params["response_format"] = response_format
        params.update(kwargs)
        return self.client.chat.completions.create(**params) 