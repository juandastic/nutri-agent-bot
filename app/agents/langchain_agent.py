"""LangChain agent for processing Telegram messages with images and attachments"""

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Path to the prompt file
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "food_analysis_prompt.txt"


class FoodAnalysisAgent:
    """Agent for analyzing food images and text to estimate nutritional values"""

    def __init__(self):
        """Initialize the food analysis agent with OpenAI GPT-4o-mini vision model"""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
        )
        self.system_prompt = self._create_system_prompt()

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for food analysis.
        Loads the prompt from a text file and injects the current datetime.

        Returns:
            str: System prompt text

        Raises:
            FileNotFoundError: If the prompt file does not exist
        """
        prompt_template = PROMPT_FILE.read_text(encoding="utf-8")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return prompt_template.format(current_datetime=current_datetime)

    async def analyze(
        self,
        text: str | None = None,
        images: list[bytes] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Analyze food from text description and/or images with conversation context.

        Args:
            text: Text description of the food (can include caption)
            images: List of image bytes to analyze
            conversation_history: List of previous messages with 'role' and 'text' keys

        Returns:
            str: Analysis response from the agent
        """
        try:
            messages = []

            # Add system message
            system_message = SystemMessage(content=self.system_prompt)
            messages.append(system_message)

            # Add conversation history if provided
            if conversation_history:
                added_count = 0
                for msg in conversation_history:
                    role = msg.get("role", "user")
                    msg_text = msg.get("text")

                    if not msg_text:
                        continue

                    if role == "user":
                        messages.append(HumanMessage(content=msg_text))
                        added_count += 1
                    elif role == "bot":
                        messages.append(AIMessage(content=msg_text))
                        added_count += 1

                logger.debug(
                    f"Added {added_count} messages from history (out of {len(conversation_history)} total)"
                )

            # Prepare user message content
            content: list[Any] = []

            # Add text if provided
            if text:
                content.append({"type": "text", "text": text})

            # Add images if provided
            if images:
                for image_bytes in images:
                    # Convert image bytes to base64
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    # Determine MIME type (assuming JPEG for Telegram photos)
                    mime_type = "image/jpeg"

                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}",
                            },
                        }
                    )

            # Create human message with content
            # If no content, add a default text
            if not content:
                content = [{"type": "text", "text": "Please analyze this food."}]

            human_message = HumanMessage(content=content)
            messages.append(human_message)

            logger.debug(
                f"Analyzing food | has_text={bool(text)} | image_count={len(images) if images else 0} | "
                f"history_count={len(conversation_history) if conversation_history else 0}"
            )

            # Call the model
            response = await self.llm.ainvoke(messages)

            response_text = response.content if hasattr(response, "content") else str(response)

            logger.info(f"Food analysis completed | response_length={len(response_text)}")

            return response_text

        except Exception as e:
            logger.error(f"Error analyzing food | error={str(e)}", exc_info=True)
            raise
