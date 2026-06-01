import asyncio
import base64
import io
import logging
from typing import Optional

from PIL import Image
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.exceptions import LLMUnavailableError

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for analyzing images using Google's Gemini API (google.genai SDK)."""

    _MODEL_NAME = "gemini-2.5-flash"

    @classmethod
    def _get_client(cls) -> genai.Client:
        return genai.Client(api_key=settings.GEMINI_API_KEY)

    @classmethod
    async def analyze_images(
        cls,
        images_b64: list[str],
        prompt: Optional[str] = None,
    ) -> str:
        """
        Analyze one or more base64-encoded images with Gemini.

        Args:
            images_b64: List of base64-encoded image strings.
            prompt: Optional user prompt to contextualize the analysis.

        Returns:
            Text description of what Gemini sees in the images.

        Raises:
            LLMUnavailableError: If the Gemini API call fails.
        """
        if not images_b64:
            return ""

        try:
            decoded_images: list[bytes] = []
            for img_b64 in images_b64:
                try:
                    if "," in img_b64:
                        img_b64 = img_b64.split(",", 1)[1]
                    decoded = base64.b64decode(img_b64)
                    decoded_images.append(decoded)
                except Exception as e:
                    logger.warning(f"Failed to decode image: {e}")
                    continue

            if not decoded_images:
                logger.warning("No valid images to analyze after decoding.")
                return ""

            default_prompt = (
                "Please analyze these images in detail and describe what you see, "
                "particularly anything relevant to health or tuberculosis."
            )
            analysis_prompt = prompt if prompt else default_prompt

            parts: list[types.Part] = [types.Part(text=analysis_prompt)]
            for image_bytes in decoded_images:
                parts.append(
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/jpeg",
                            data=image_bytes,
                        )
                    )
                )

            contents = [types.Content(role="user", parts=parts)]
            client = cls._get_client()

            response = await client.aio.models.generate_content(
                model=cls._MODEL_NAME,
                contents=contents,
            )

            analysis_text = response.text or "No analysis provided."
            logger.info(f"Gemini image analysis completed: {analysis_text[:200]}...")
            return analysis_text

        except Exception as e:
            logger.error(f"Gemini image analysis failed: {e}")
            raise LLMUnavailableError(f"Gemini image analysis error: {e}")

    @classmethod
    def combine_with_user_message(
        cls,
        user_message: str,
        image_analysis: str,
    ) -> str:
        """
        Combine Gemini's image analysis with the user's message.

        The format matches the existing system-note pattern so downstream
        nodes (guardrails, NLU, generation) can still parse it correctly.
        """
        return (
            f"[System Note: User attached images. Image Analysis: {image_analysis}]\n\n"
            f"User message: {user_message}"
        )
