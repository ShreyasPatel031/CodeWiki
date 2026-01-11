"""
LLM service factory for creating configured LLM clients.
"""
import os
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModelSettings
from pydantic_ai.models.fallback import FallbackModel
from openai import OpenAI

from codewiki.src.config import Config


def create_main_model(config: Config) -> OpenAIModel:
    """Create the main LLM model from configuration."""
    # Set environment variable - OpenAIProvider reads from OPENAI_API_KEY
    os.environ['OPENAI_API_KEY'] = config.llm_api_key
    
    # Create provider - OpenAIProvider reads API key from OPENAI_API_KEY env var
    # For OpenAI's standard API endpoint, we don't need to pass base_url
    provider = OpenAIProvider()
    
    # gpt-4o supports max 16384 tokens, other models may support more
    # Use 16384 as safe default for gpt-4o, adjust if needed for other models
    max_tokens = 16384 if 'gpt-4o' in config.main_model.lower() else 32768
    
    return OpenAIModel(
        model_name=config.main_model,
        provider=provider,
        settings=OpenAIModelSettings(
            temperature=0.0,
            max_tokens=max_tokens
        )
    )


def create_fallback_model(config: Config) -> OpenAIModel:
    """Create the fallback LLM model from configuration."""
    # Set environment variable - OpenAIProvider reads from OPENAI_API_KEY
    os.environ['OPENAI_API_KEY'] = config.llm_api_key
    
    # Create provider - OpenAIProvider reads API key from OPENAI_API_KEY env var
    # For OpenAI's standard API endpoint, we don't need to pass base_url
    provider = OpenAIProvider()
    
    # gpt-4o supports max 16384 tokens, other models may support more
    # Use 16384 as safe default for gpt-4o, adjust if needed for other models
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
    import logging
    import time
    from codewiki.src.be.utils import count_tokens
    
    logger = logging.getLogger(__name__)
    
    if model is None:
        model = config.main_model
    
    # Calculate prompt token count
    prompt_tokens = count_tokens(prompt)
    logger.info(f"[LLM] Preparing LLM call: model={model}, prompt_tokens={prompt_tokens}, temperature={temperature}")
    logger.info(f"[LLM] Base URL: {config.llm_base_url}")
    
    client = create_openai_client(config)
    # gpt-4o supports max 16384 tokens, other models may support more
    max_tokens = 16384 if 'gpt-4o' in model.lower() else 32768
    logger.info(f"[LLM] Max tokens: {max_tokens}")
    
    try:
        llm_start = time.time()
        logger.info(f"[LLM] Sending request to LLM API...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        llm_duration = time.time() - llm_start
        logger.info(f"[LLM] LLM call completed in {llm_duration:.1f}s")
        
        # Extract response content
        response_content = response.choices[0].message.content
        response_tokens = count_tokens(response_content)
        logger.info(f"[LLM] Response length: {len(response_content)} chars, {response_tokens} tokens")
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        llm_duration = time.time() - llm_start if 'llm_start' in locals() else 0
        logger.error(f"[LLM] LLM call FAILED after {llm_duration:.1f}s: {error_type}: {error_msg}")
        
        # Detect specific error types
        if "429" in error_msg or "rate limit" in error_msg.lower() or "RateLimitError" in error_type:
            logger.error(f"[LLM] RATE LIMIT DETECTED!")
            logger.error(f"[LLM]   - Model: {model}")
            logger.error(f"[LLM]   - Prompt tokens: {prompt_tokens}")
            logger.error(f"[LLM]   - Base URL: {config.llm_base_url}")
            if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                retry_after = e.response.headers.get('Retry-After', 'unknown')
                logger.error(f"[LLM]   - Retry-After header: {retry_after}")
        elif "401" in error_msg or "authentication" in error_msg.lower() or "AuthenticationError" in error_type:
            logger.error(f"[LLM] AUTHENTICATION ERROR!")
            logger.error(f"[LLM]   - Model: {model}")
            logger.error(f"[LLM]   - Base URL: {config.llm_base_url}")
        elif "timeout" in error_msg.lower():
            logger.error(f"[LLM] TIMEOUT ERROR!")
            logger.error(f"[LLM]   - Model: {model}")
            logger.error(f"[LLM]   - Prompt tokens: {prompt_tokens}")
        
        import traceback
        logger.error(f"[LLM] Traceback: {traceback.format_exc()}")
        raise
    
    # Track token usage for metrics
    try:
        from codewiki.src.utils.metrics import get_metrics_collector
        metrics = get_metrics_collector().get_current()
        if metrics and hasattr(response, 'usage'):
            tokens_used = (response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0) + \
                         (response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0)
            logger.info(f"[LLM] Token usage - Prompt: {response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0}, Completion: {response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0}, Total: {tokens_used}")
            # Add to current stage if available
            if hasattr(metrics, 'stages') and metrics.stages:
                # Add to the most recent stage
                latest_stage = list(metrics.stages.values())[-1] if metrics.stages else None
                if latest_stage:
                    latest_stage.tokens_used += tokens_used
    except Exception as ex:
        logger.debug(f"[LLM] Metrics tracking failed (non-critical): {ex}")
    
    return response_content