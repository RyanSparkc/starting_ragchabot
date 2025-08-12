import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai


class AIGenerator:
    """Handles interactions with Google Gemini API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant for a course materials system. You have access to a search tool for course content.

CRITICAL: You MUST use the search_course_content function for ANY question that could be about course materials, including:
- Questions about courses, lessons, or educational content
- Questions mentioning "MCP", "Anthropic", "Computer Use", "Retrieval", "Prompt", "Chroma", or similar terms
- Any question that might have an answer in the course database

ALWAYS search first, then provide your answer based on the search results.

Example questions that require search:
- "What is MCP?"
- "Tell me about Anthropic"
- "How does retrieval work?"
- "What are the course topics?"

When you search and find results, provide a comprehensive answer based on the found information.
If no results are found, then use your general knowledge.

Be direct and helpful in your responses."""

    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

        # Configuration for generation
        self.generation_config = {
            "temperature": 0,
            "max_output_tokens": 800,
        }

        # Safety settings - very permissive for educational content
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
        ]

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build prompt with system instructions and conversation history
        full_prompt = self.SYSTEM_PROMPT
        if conversation_history:
            full_prompt += f"\n\nPrevious conversation:\n{conversation_history}"
        full_prompt += f"\n\nUser question: {query}"

        # Convert tools for Gemini format if available
        gemini_tools = None
        if tools:
            gemini_tools = self._convert_tools_to_gemini_format(tools)

        try:
            # Generate response with Gemini
            if gemini_tools:
                response = self.model.generate_content(
                    full_prompt,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                    tools=gemini_tools,
                )

                # Handle function calling if needed
                if (
                    response.candidates
                    and len(response.candidates) > 0
                    and response.candidates[0].content
                    and response.candidates[0].content.parts
                    and tool_manager
                ):
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            return self._handle_gemini_function_call(
                                part.function_call, tool_manager, full_prompt
                            )
            else:
                response = self.model.generate_content(
                    full_prompt,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings,
                )

            # Safely extract text from response with proper error handling
            if response and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]

                # Check finish_reason for safety filters or other issues
                if hasattr(candidate, "finish_reason"):
                    if candidate.finish_reason == 2:  # SAFETY
                        return "I'm having trouble processing your question about course materials. This appears to be an educational query, so please try rephrasing it or contact support if this continues."
                    elif candidate.finish_reason == 3:  # RECITATION
                        return "I cannot provide that specific response due to content policy. Please try asking in a different way."
                    elif candidate.finish_reason == 4:  # OTHER
                        return "I encountered a technical issue generating a response. Please try again with your question."

                # Try to extract text safely
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            try:
                                return (
                                    str(part.text)
                                    .encode("utf-8", errors="replace")
                                    .decode("utf-8")
                                )
                            except:
                                return part.text

                # If no text content, check if there are function calls without text
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            # This should be handled by function call logic above
                            return "Processing your request..."

            # Fallback - try direct text access with error handling
            try:
                if response and hasattr(response, "text") and response.text:
                    return (
                        str(response.text)
                        .encode("utf-8", errors="replace")
                        .decode("utf-8")
                    )
            except Exception:
                pass  # Fall through to default message

            return "I apologize, but I couldn't generate a response. Please try again."

        except UnicodeEncodeError as e:
            return "I apologize, there was an encoding issue with the response. Please try again."
        except Exception as e:
            # Handle encoding issues in error messages
            try:
                error_msg = str(e).encode("utf-8", errors="replace").decode("utf-8")
                return f"Error generating response: {error_msg}"
            except:
                return "Error generating response. Please try again."

    def _convert_tools_to_gemini_format(self, tools: List) -> List:
        """Convert Claude tool format to Gemini function format"""
        gemini_tools = []
        for tool in tools:
            gemini_tool = {
                "function_declarations": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    }
                ]
            }
            gemini_tools.append(gemini_tool)
        return gemini_tools

    def _handle_gemini_function_call(
        self, function_call, tool_manager, original_prompt
    ):
        """
        Handle Gemini function calling and get follow-up response.

        Args:
            function_call: The function call from Gemini
            tool_manager: Manager to execute tools
            original_prompt: The original prompt for context

        Returns:
            Final response text after tool execution
        """
        try:
            # Execute the function call
            function_name = function_call.name

            # Convert protobuf args to dict properly
            function_args = {}
            if function_call.args:
                if hasattr(function_call.args, "fields"):
                    # Handle protobuf Struct format
                    for key, value in function_call.args.fields.items():
                        if hasattr(value, "string_value") and value.string_value:
                            function_args[key] = value.string_value
                        elif hasattr(value, "number_value"):
                            function_args[key] = (
                                int(value.number_value)
                                if value.number_value.is_integer()
                                else value.number_value
                            )
                        elif hasattr(value, "bool_value"):
                            function_args[key] = value.bool_value
                        elif hasattr(value, "list_value"):
                            function_args[key] = [
                                item.string_value for item in value.list_value.values
                            ]
                        else:
                            # Fallback
                            function_args[key] = str(value)
                else:
                    # Handle dict-like format (fallback)
                    try:
                        function_args = dict(function_call.args)
                    except:
                        pass  # Use empty dict

            tool_result = tool_manager.execute_tool(function_name, **function_args)

            # Create follow-up prompt with tool result
            follow_up_prompt = f"{original_prompt}\n\nFunction call result: {tool_result}\n\nBased on this information, provide a comprehensive answer:"

            # Generate final response
            response = self.model.generate_content(
                follow_up_prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
            )

            # Safely extract text from response with proper error handling
            if response and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]

                # Check finish_reason for safety filters or other issues
                if hasattr(candidate, "finish_reason"):
                    if candidate.finish_reason == 2:  # SAFETY
                        return "I'm having trouble processing your question about course materials. This appears to be an educational query, so please try rephrasing it or contact support if this continues."
                    elif candidate.finish_reason == 3:  # RECITATION
                        return "I cannot provide that specific response due to content policy. Please try asking in a different way."
                    elif candidate.finish_reason == 4:  # OTHER
                        return "I encountered a technical issue generating a response. Please try again with your question."

                # Try to extract text safely
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            try:
                                return (
                                    str(part.text)
                                    .encode("utf-8", errors="replace")
                                    .decode("utf-8")
                                )
                            except:
                                return part.text

            # Fallback - try direct text access with error handling
            try:
                if response and hasattr(response, "text") and response.text:
                    return (
                        str(response.text)
                        .encode("utf-8", errors="replace")
                        .decode("utf-8")
                    )
            except Exception:
                pass  # Fall through to default message

            return f"Based on the search results: {tool_result}"

        except UnicodeEncodeError as e:
            return "I apologize, there was an encoding issue with the function response. Please try again."
        except Exception as e:
            # Handle encoding issues in error messages
            try:
                error_msg = str(e).encode("utf-8", errors="replace").decode("utf-8")
                return f"Error executing function: {error_msg}"
            except:
                return "Error executing function. Please try again."
