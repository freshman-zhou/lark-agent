from pathlib import Path


class PromptLoader:
    @staticmethod
    def load(prompt_name: str) -> str:
        root = Path(__file__).resolve().parents[1]
        prompt_path = root / "prompts" / prompt_name

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")