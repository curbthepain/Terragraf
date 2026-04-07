"""
Concrete LLM provider implementations.

AnthropicProvider — Claude via anthropic SDK
OpenAICompatibleProvider — OpenAI, Qwen, DeepSeek, ollama, vllm, lmstudio via openai SDK
"""

from typing import Iterator

from .base import LLMProvider, LLMConfig, LLMContext


ANTHROPIC_DEFAULT_MODEL = "claude-3-5-haiku-20241022"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


def _format_context_block(context: LLMContext) -> str:
    """Build a compact context summary from route/header matches."""
    lines = []
    if context.route_matches:
        lines.append("Scaffold route matches (partial):")
        for rm in context.route_matches[:5]:
            score_pct = int(rm.score * 100) if hasattr(rm, "score") else 0
            concept = rm.concept if hasattr(rm, "concept") else str(rm)
            path = rm.path if hasattr(rm, "path") else ""
            lines.append(f"  {concept} -> {path} [{score_pct}%]")
    if context.header_matches:
        lines.append("Scaffold header matches (partial):")
        for hm in context.header_matches[:3]:
            name = hm.module_name if hasattr(hm, "module_name") else str(hm)
            lines.append(f"  #{name}")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are an assistant embedded in Terragraf, a scaffolding system for "
    "compute, visualization, and ML projects. Answer the user's question. "
    "If scaffold context is provided below, use it to ground your answer.\n\n"
)


class AnthropicProvider(LLMProvider):
    """Claude provider via the anthropic SDK."""

    def __init__(self, config: LLMConfig):
        self._config = config
        self._model = config.model or ANTHROPIC_DEFAULT_MODEL

    def stream(self, context: LLMContext) -> Iterator[str]:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic SDK not installed. Run: pip install anthropic"
            )

        if not self._config.api_key:
            raise RuntimeError("No API key configured for anthropic provider")

        client = anthropic.Anthropic(api_key=self._config.api_key)

        system = SYSTEM_PROMPT
        ctx_block = _format_context_block(context)
        if ctx_block:
            system += ctx_block

        with client.messages.stream(
            model=self._model,
            max_tokens=self._config.max_tokens,
            system=system,
            messages=[{"role": "user", "content": context.query}],
            temperature=self._config.temperature,
        ) as stream:
            for text in stream.text_stream:
                yield text

    def validate(self) -> bool:
        try:
            import anthropic
            return bool(self._config.api_key)
        except ImportError:
            return False


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible provider (OpenAI, Qwen, DeepSeek, ollama, vllm, lmstudio)."""

    def __init__(self, config: LLMConfig):
        self._config = config
        self._model = config.model or OPENAI_DEFAULT_MODEL

    def stream(self, context: LLMContext) -> Iterator[str]:
        try:
            import openai
        except ImportError:
            raise RuntimeError(
                "openai SDK not installed. Run: pip install openai"
            )

        if not self._config.api_key:
            raise RuntimeError("No API key configured for openai provider")

        kwargs = {"api_key": self._config.api_key}
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url

        client = openai.OpenAI(**kwargs)

        system = SYSTEM_PROMPT
        ctx_block = _format_context_block(context)
        if ctx_block:
            system += ctx_block

        response = client.chat.completions.create(
            model=self._model,
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": context.query},
            ],
            stream=True,
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def validate(self) -> bool:
        try:
            import openai
            return bool(self._config.api_key)
        except ImportError:
            return False


HUGGINGFACE_DEFAULT_MODEL = "sshleifer/tiny-gpt2"


class HuggingFaceProvider(LLMProvider):
    """
    Local inference via transformers.pipeline. Lazy-imports torch + transformers
    so that constructing the provider does not pull heavy deps into the LLM
    startup path. Streams tokens via TextIteratorStreamer so the existing
    LLMWorker (.scaffold/app/llm_worker.py) needs no changes.
    """

    def __init__(self, config: LLMConfig):
        self._config = config
        self._model_id = config.model or HUGGINGFACE_DEFAULT_MODEL
        self._pipeline = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline, AutoTokenizer  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "transformers not installed. Run: "
                "pip install transformers torch"
            ) from e

        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)
        self._pipeline = pipeline(
            "text-generation",
            model=self._model_id,
            tokenizer=self._tokenizer,
            device_map="auto",
        )

    def stream(self, context: LLMContext) -> Iterator[str]:
        self._load()
        try:
            from transformers import TextIteratorStreamer  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "transformers not installed. Run: pip install transformers"
            ) from e
        from threading import Thread

        prompt = SYSTEM_PROMPT
        ctx_block = _format_context_block(context)
        if ctx_block:
            prompt += ctx_block + "\n\n"
        prompt += f"User: {context.query}\nAssistant: "

        assert self._tokenizer is not None and self._pipeline is not None
        inputs = self._tokenizer(prompt, return_tensors="pt")
        device = getattr(self._pipeline.model, "device", None)
        if device is not None:
            inputs = {k: v.to(device) for k, v in inputs.items()}

        streamer = TextIteratorStreamer(
            self._tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs = {
            **inputs,
            "streamer": streamer,
            "max_new_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
            "do_sample": self._config.temperature > 0,
        }
        thread = Thread(
            target=self._pipeline.model.generate,
            kwargs=gen_kwargs,
            daemon=True,
        )
        thread.start()
        for token in streamer:
            yield token
        thread.join()

    def validate(self) -> bool:
        try:
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False
