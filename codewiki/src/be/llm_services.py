"""
LLM service factory for creating configured LLM clients.
"""
import os
import logging
import time
from dataclasses import dataclass, field
from typing import Dict
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModelSettings
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models import Model
from openai import OpenAI

# Try to import Gemini support (use GoogleModel, not deprecated GeminiModel)
try:
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        # Fallback to deprecated GeminiModel
        from pydantic_ai.models.gemini import GeminiModel as GoogleModel
        from pydantic_ai.providers.google import GoogleProvider
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False
        GoogleProvider = None
        GoogleModel = None

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from codewiki.src.config import Config

logger = logging.getLogger(__name__)


# =============================================================================
# GLOBAL TOKEN TRACKER - Accurate cost measurement across all LLM calls
# =============================================================================

# GPT-4o pricing (as of Jan 2025)
PRICING = {
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},  # $2.50/1M input, $10/1M output
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4-turbo": {"input": 10.00 / 1_000_000, "output": 30.00 / 1_000_000},
    "claude-sonnet-4": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "default": {"input": 5.00 / 1_000_000, "output": 15.00 / 1_000_000},
}


@dataclass
class LLMCallStats:
    """Statistics for a single LLM call."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    duration_seconds: float
    stage: str = ""
    success: bool = True
    error: str = ""
    
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens
    
    @property
    def cost(self) -> float:
        pricing = PRICING.get(self.model.lower(), PRICING["default"])
        return (self.prompt_tokens * pricing["input"]) + (self.completion_tokens * pricing["output"])


@dataclass
class TokenTracker:
    """Global tracker for all LLM calls and costs."""
    calls: list = field(default_factory=list)
    current_stage: str = ""
    
    def add_call(self, stats: LLMCallStats):
        stats.stage = self.current_stage
        self.calls.append(stats)
        
        # Log the call
        logger.info(f"[TOKEN TRACKER] Call #{len(self.calls)}: {stats.model}")
        logger.info(f"[TOKEN TRACKER]   Stage: {stats.stage}")
        logger.info(f"[TOKEN TRACKER]   Prompt tokens: {stats.prompt_tokens:,}")
        logger.info(f"[TOKEN TRACKER]   Completion tokens: {stats.completion_tokens:,}")
        logger.info(f"[TOKEN TRACKER]   Total tokens: {stats.total_tokens:,}")
        logger.info(f"[TOKEN TRACKER]   Duration: {stats.duration_seconds:.1f}s")
        logger.info(f"[TOKEN TRACKER]   Cost: ${stats.cost:.4f}")
        logger.info(f"[TOKEN TRACKER]   Running total: ${self.total_cost:.4f}")
    
    def set_stage(self, stage: str):
        self.current_stage = stage
        logger.info(f"[TOKEN TRACKER] === Stage: {stage} ===")
    
    @property
    def total_prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)
    
    @property
    def total_completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)
    
    @property
    def total_tokens(self) -> int:
        return self.total_prompt_tokens + self.total_completion_tokens
    
    @property
    def total_cost(self) -> float:
        return sum(c.cost for c in self.calls)
    
    @property
    def successful_calls(self) -> int:
        return sum(1 for c in self.calls if c.success)
    
    @property
    def failed_calls(self) -> int:
        return sum(1 for c in self.calls if not c.success)
    
    def get_summary(self) -> str:
        """Get a formatted summary of all LLM usage."""
        lines = [
            "=" * 60,
            "LLM USAGE SUMMARY",
            "=" * 60,
            f"Total calls: {len(self.calls)} ({self.successful_calls} successful, {self.failed_calls} failed)",
            f"Total prompt tokens: {self.total_prompt_tokens:,}",
            f"Total completion tokens: {self.total_completion_tokens:,}",
            f"Total tokens: {self.total_tokens:,}",
            f"TOTAL COST: ${self.total_cost:.4f}",
            "",
            "By Stage:",
        ]
        
        # Group by stage
        by_stage: Dict[str, list] = {}
        for call in self.calls:
            if call.stage not in by_stage:
                by_stage[call.stage] = []
            by_stage[call.stage].append(call)
        
        for stage, calls in by_stage.items():
            stage_cost = sum(c.cost for c in calls)
            stage_tokens = sum(c.total_tokens for c in calls)
            lines.append(f"  {stage or 'Unknown'}: {len(calls)} calls, {stage_tokens:,} tokens, ${stage_cost:.4f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def reset(self):
        """Reset the tracker for a new run."""
        self.calls = []
        self.current_stage = ""


# Global singleton
_token_tracker = TokenTracker()


def get_token_tracker() -> TokenTracker:
    """Get the global token tracker."""
    return _token_tracker


def _is_gemini_model(model_name: str) -> bool:
    """Check if model name indicates Gemini."""
    return 'gemini' in model_name.lower()


def create_main_model(config: Config) -> Model:
    """Create the main LLM model from configuration."""
    
    # Native Gemini support - use pydantic_ai's GoogleModel
    if _is_gemini_model(config.main_model) and GEMINI_AVAILABLE:
        logger.info(f"[LLM] Using native Gemini support for {config.main_model}")
        # Set environment variable for GoogleProvider to pick up
        os.environ['GEMINI_API_KEY'] = config.llm_api_key
        return GoogleModel(
            model_name=config.main_model,
            provider='google-gla'  # Use string provider, API key from env
        )
    
    # OpenAI or OpenAI-compatible endpoint
    os.environ['OPENAI_API_KEY'] = config.llm_api_key
    provider = OpenAIProvider(base_url=config.llm_base_url, api_key=config.llm_api_key)
    max_tokens = 16384 if 'gpt-4o' in config.main_model.lower() else 32768
    
    return OpenAIModel(
        model_name=config.main_model,
        provider=provider,
        settings=OpenAIModelSettings(
            temperature=0.0,
            max_tokens=max_tokens
        )
    )


def create_fallback_model(config: Config) -> Model:
    """Create the fallback LLM model from configuration."""
    
    # Native Gemini support
    if _is_gemini_model(config.fallback_model) and GEMINI_AVAILABLE:
        logger.info(f"[LLM] Using native Gemini support for fallback {config.fallback_model}")
        os.environ['GEMINI_API_KEY'] = config.llm_api_key
        return GoogleModel(
            model_name=config.fallback_model,
            provider='google-gla'
        )
    
    # OpenAI or OpenAI-compatible endpoint
    os.environ['OPENAI_API_KEY'] = config.llm_api_key
    provider = OpenAIProvider(base_url=config.llm_base_url, api_key=config.llm_api_key)
    max_tokens = 16384 if 'gpt-4o' in config.fallback_model.lower() else 32768
    
    return OpenAIModel(
        model_name=config.fallback_model,
        provider=provider,
        settings=OpenAIModelSettings(
            temperature=0.0,
            max_tokens=max_tokens
        )
    )


def create_fallback_models(config: Config) -> FallbackModel:
    """Create fallback models chain from configuration."""
    main = create_main_model(config)
    fallback = create_fallback_model(config)
    return FallbackModel(main, fallback)


def create_openai_client(config: Config) -> OpenAI:
    """Create OpenAI client from configuration."""
    return OpenAI(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key
    )


def _call_gemini_native(
    prompt: str,
    config: Config,
    model: str,
    temperature: float
) -> str:
    """Call Gemini LLM using native Google Generative AI client."""
    from codewiki.src.be.utils import count_tokens
    
    tracker = get_token_tracker()
    prompt_tokens_estimated = count_tokens(prompt)
    
    logger.info(f"[LLM] Using native Gemini API for {model}")
    
    # Prefer GEMINI_API_KEY env var, fallback to config
    api_key = os.getenv('GEMINI_API_KEY') or config.llm_api_key
    genai.configure(api_key=api_key)
    genai_model = genai.GenerativeModel(model)
    
    llm_start = time.time()
    try:
        response = genai_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=32768
            )
        )
        llm_duration = time.time() - llm_start
        
        response_text = response.text
        
        # Get token counts from usage metadata if available
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            actual_prompt_tokens = response.usage_metadata.prompt_token_count
            actual_completion_tokens = response.usage_metadata.candidates_token_count
        else:
            actual_prompt_tokens = prompt_tokens_estimated
            actual_completion_tokens = count_tokens(response_text)
        
        stats = LLMCallStats(
            model=model,
            prompt_tokens=actual_prompt_tokens,
            completion_tokens=actual_completion_tokens,
            duration_seconds=llm_duration,
            success=True
        )
        tracker.add_call(stats)
        
        return response_text
        
    except Exception as e:
        llm_duration = time.time() - llm_start
        logger.error(f"[LLM] Gemini API error: {type(e).__name__}: {str(e)}")
        stats = LLMCallStats(
            model=model,
            prompt_tokens=prompt_tokens_estimated,
            completion_tokens=0,
            duration_seconds=llm_duration,
            success=False,
            error=str(e)
        )
        tracker.add_call(stats)
        raise


def call_llm(
    prompt: str,
    config: Config,
    model: str = None,
    temperature: float = 0.0
) -> str:
    """
    Call LLM with the given prompt.
    
    Args:
        prompt: The prompt to send
        config: Configuration containing LLM settings
        model: Model name (defaults to config.main_model)
        temperature: Temperature setting
        
    Returns:
        LLM response text
    """
    from codewiki.src.be.utils import count_tokens
    
    tracker = get_token_tracker()
    
    if model is None:
        model = config.main_model
    
    # Use native Gemini if available
    if _is_gemini_model(model) and GENAI_AVAILABLE:
        return _call_gemini_native(prompt, config, model, temperature)
    
    # Calculate prompt token count
    prompt_tokens_estimated = count_tokens(prompt)
    logger.info(f"[LLM] Preparing LLM call: model={model}, prompt_tokens={prompt_tokens_estimated:,}, temperature={temperature}")
    
    client = create_openai_client(config)
    # gpt-4o supports max 16384 tokens, other models may support more
    max_tokens = 16384 if 'gpt-4o' in model.lower() else 32768
    logger.info(f"[LLM] Max tokens: {max_tokens}")
    
    llm_start = time.time()
    try:
        logger.info(f"[LLM] Sending request to LLM API...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        llm_duration = time.time() - llm_start
        
        # Extract response content
        response_content = response.choices[0].message.content
        
        # Get actual token counts from API response (more accurate)
        if hasattr(response, 'usage') and response.usage:
            actual_prompt_tokens = response.usage.prompt_tokens
            actual_completion_tokens = response.usage.completion_tokens
        else:
            # Fall back to estimation
            actual_prompt_tokens = prompt_tokens_estimated
            actual_completion_tokens = count_tokens(response_content)
        
        # Track the call
        stats = LLMCallStats(
            model=model,
            prompt_tokens=actual_prompt_tokens,
            completion_tokens=actual_completion_tokens,
            duration_seconds=llm_duration,
            success=True
        )
        tracker.add_call(stats)
        
        logger.info(f"[LLM] LLM call completed in {llm_duration:.1f}s")
        logger.info(f"[LLM] Response: {len(response_content)} chars, {actual_completion_tokens:,} tokens")
        
    except Exception as e:
        llm_duration = time.time() - llm_start
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Track the failed call (still costs money for prompt tokens!)
        stats = LLMCallStats(
            model=model,
            prompt_tokens=prompt_tokens_estimated,  # We still sent these
            completion_tokens=0,
            duration_seconds=llm_duration,
            success=False,
            error=f"{error_type}: {error_msg[:100]}"
        )
        tracker.add_call(stats)
        
        logger.error(f"[LLM] LLM call FAILED after {llm_duration:.1f}s: {error_type}: {error_msg}")
        
        # Detect specific error types
        if "429" in error_msg or "rate limit" in error_msg.lower() or "RateLimitError" in error_type:
            logger.error(f"[LLM] RATE LIMIT DETECTED!")
        elif "context_length_exceeded" in error_msg.lower() or "context length" in error_msg.lower():
            logger.error(f"[LLM] CONTEXT LENGTH EXCEEDED!")
            logger.error(f"[LLM]   - Prompt tokens: {prompt_tokens_estimated:,}")
            logger.error(f"[LLM]   - Max context: 128,000 (gpt-4o)")
        elif "401" in error_msg or "authentication" in error_msg.lower():
            logger.error(f"[LLM] AUTHENTICATION ERROR!")
        elif "timeout" in error_msg.lower():
            logger.error(f"[LLM] TIMEOUT ERROR!")
        
        import traceback
        logger.error(f"[LLM] Traceback: {traceback.format_exc()}")
        raise
    
    # Also track in old metrics system for compatibility
    try:
        from codewiki.src.utils.metrics import get_metrics_collector
        metrics = get_metrics_collector().get_current()
        if metrics and hasattr(metrics, 'stages') and metrics.stages:
            latest_stage = list(metrics.stages.values())[-1] if metrics.stages else None
            if latest_stage:
                latest_stage.tokens_used += stats.total_tokens
    except Exception:
        pass  # Non-critical
    
    return response_content