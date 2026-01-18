import ollama
import os

class OllamaService:
    def __init__(self, url: str = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')):
        self.model_list = []
        self.url = url

    def get_model_list(self):
        self.model_list = ollama.list()['models']
        return self.model_list