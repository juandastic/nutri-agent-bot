"""LangChain agent for processing Telegram messages with images and attachments"""

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langsmith import traceable

from app.config import settings
from app.tools.spreadsheet_tool import create_register_nutritional_info_tool
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Path to the prompt file
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "food_analysis_prompt.txt"

# Set LangSmith environment variables if configured
if settings.LANGSMITH_API_KEY:
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
if settings.LANGSMITH_TRACING == "true":
    os.environ["LANGSMITH_TRACING"] = "true"
if settings.LANGSMITH_PROJECT:
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT


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

    def _get_agent(self, user_id: int, redirect_uri: str | None = None) -> Runnable:
        """
        Get or create agent with tools bound to user_id.

        Args:
            user_id: Internal user ID (from database)
            redirect_uri: OAuth redirect URI (optional, for dynamic URL generation)

        Returns:
            Runnable: Compiled agent graph
        """
        # Create tool bound to user_id and redirect_uri
        bound_tools = [create_register_nutritional_info_tool(user_id, redirect_uri)]

        # Create agent using LangChain 1.0 API
        agent = create_agent(
            model=self.llm,
            tools=bound_tools,
            system_prompt=self.system_prompt,
        )

        return agent

    @traceable(
        name="FoodAnalysisAgent.analyze",
        run_type="chain",
        tags=["food-analysis", "agent"],
    )
    async def analyze(
        self,
        text: str | None = None,
        images: list[bytes] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        user_id: int | None = None,
        redirect_uri: str | None = None,
    ) -> str:
        """
        Analyze food from text description and/or images with conversation context.

        Args:
            text: Text description of the food (can include caption)
            images: List of image bytes to analyze
            conversation_history: List of previous messages with 'role' and 'text' keys
            user_id: Internal user ID (from database, required for tools)
            redirect_uri: OAuth redirect URI (optional)

        Returns:
            str: Analysis response from the agent
        """
        try:
            logger.debug(
                f"Analyzing food | has_text={bool(text)} | image_count={len(images) if images else 0} | "
                f"history_count={len(conversation_history) if conversation_history else 0} | "
                f"user_id={user_id}"
            )

            # Build input text
            input_text = text if text else ""

            # Convert conversation history to LangChain format
            chat_history = []
            if conversation_history:
                for msg in conversation_history:
                    role = msg.get("role", "user")
                    msg_text = msg.get("text")
                    if msg_text:
                        if role == "user":
                            chat_history.append(HumanMessage(content=msg_text))
                        elif role == "bot":
                            chat_history.append(AIMessage(content=msg_text))

            # Use agent executor with tools for all messages
            # user_id should always be provided from Telegram
            if user_id is None:
                raise ValueError("user_id is required for agent execution")

            agent = self._get_agent(user_id, redirect_uri)

            # Build messages for the agent
            messages = []
            if chat_history:
                messages.extend(chat_history)

            # Prepare user message content
            if images:
                # Prepare user message content with images
                content: list[Any] = []
                if input_text:
                    content.append({"type": "text", "text": input_text})

                for image_bytes in images:
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    mime_type = "image/jpeg"
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                        }
                    )

                if not content:
                    content = [{"type": "text", "text": "Please analyze this food."}]

                messages.append(HumanMessage(content=content))
            else:
                # Text-only message
                messages.append(HumanMessage(content=input_text))

            # Invoke the agent
            result = await agent.ainvoke({"messages": messages})

            # Extract response from agent result
            if isinstance(result, dict):
                if "messages" in result and result["messages"]:
                    last_message = result["messages"][-1]
                    response_text = (
                        last_message.content
                        if hasattr(last_message, "content")
                        else str(last_message)
                    )
                else:
                    response_text = str(result)
            else:
                response_text = str(result)

            logger.info(f"Food analysis completed | response_length={len(response_text)}")

            return response_text

        except Exception as e:
            logger.error(f"Error analyzing food | error={str(e)}", exc_info=True)
            raise
