"""
LLM Provider Router
Supports OpenAI, Anthropic (Claude), and Google Gemini.
Provider is selected at runtime based on settings.
"""
import json
from django.conf import settings


class LLMRouter:
    """
    Routes LLM calls to the configured provider.
    Set MARKETING_AGENT_PROVIDER in settings to: 'openai', 'anthropic', or 'gemini'
    """

    @staticmethod
    def complete(system_prompt: str, user_prompt: str) -> str:
        """Send prompts to the configured LLM and return the text response."""
        provider = getattr(settings, 'MARKETING_AGENT_PROVIDER', 'openai').lower()

        if provider == 'openai':
            return LLMRouter._call_openai(system_prompt, user_prompt)
        elif provider == 'anthropic':
            return LLMRouter._call_anthropic(system_prompt, user_prompt)
        elif provider == 'gemini':
            return LLMRouter._call_gemini(system_prompt, user_prompt)
        else:
            raise ValueError(f"Proveedor LLM no soportado: '{provider}'. Usa: openai, anthropic, gemini")

    @staticmethod
    def _call_openai(system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    @staticmethod
    def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    @staticmethod
    def _call_gemini(system_prompt: str, user_prompt: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-pro'),
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_prompt)
        return response.text
