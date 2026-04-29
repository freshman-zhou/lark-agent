from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        raise NotImplementedError