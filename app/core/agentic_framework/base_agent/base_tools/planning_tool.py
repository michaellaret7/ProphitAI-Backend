"""Planning tool for creating structured task plans using Pydantic models."""

import instructor
from openai import OpenAI
from typing import Dict, Any
from dotenv import load_dotenv
from app.core.agentic_framework.base_agent.tasks.models import TodoList, MainTask, SubTask, TaskStatus
load_dotenv()

class PlanningTool:
    """Tool for creating structured plans using instructor and Pydantic models."""
    
    def __init__(self, agent=None):
        """Initialize the planning tool with instructor-patched OpenAI client and optional agent."""
        self.client = instructor.from_openai(OpenAI())
        self.agent = agent
    
    def _format_tools_for_prompt(self, tools_info: Dict[str, Dict[str, Any]]) -> str:
        """Format structured tools information for LLM prompt."""
        formatted_tools = []
        for tool_name, tool_data in tools_info.items():
            description = tool_data.get('description', 'No description')
            required_params = tool_data.get('required', [])
            
            tool_text = f"• {tool_name}: {description}"
            if required_params:
                tool_text += f" (Required: {', '.join(required_params)})"
            formatted_tools.append(tool_text)
        
        return "\n".join(formatted_tools)
    
    def _extract_agent_context(self) -> Dict[str, Any]:
        """Extract context from the agent instance if available."""
        if not self.agent:
            return {}
        
        context = {}
        
        # Extract system and user prompts
        context['system_prompt'] = getattr(self.agent, 'system_prompt', '')
        context['user_prompt'] = getattr(self.agent, 'user_prompt', '')
        
        # Extract available tools
        if hasattr(self.agent, 'get_available_tools'):
            context['available_tools'] = self.agent.get_available_tools()
        else:
            context['available_tools'] = {}
        
        # Extract semantic memory context
        if hasattr(self.agent, 'semantic_memory') and self.agent.semantic_memory:
            context['memory_context'] = self.agent.semantic_memory.format_memories_for_prompt(concise=True)
        else:
            context['memory_context'] = ''
        
        # For now, role_prompt is same as system_prompt (can be extended later)
        context['role_prompt'] = context['system_prompt']
        
        return context
    
    def create_structured_plan(
        self,
        memory_context: str = "",
        available_tools = None,
        system_prompt: str = "",
        role_prompt: str = "",
        user_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Create a structured plan using Pydantic models.
        
        Args:
            memory_context: Semantic memory context if available
            available_tools: Structured tools info dict, list, or string representation
            system_prompt: The system prompt providing context and instructions
            role_prompt: The role prompt for the agent
            user_prompt: The original user prompt/query
        Returns:
            Dict containing the TodoList as JSON or error information
        """
        try:
            # Extract agent context if parameters not provided and agent is available
            agent_context = self._extract_agent_context()
            
            # Use agent context as defaults if parameters not provided
            memory_context = memory_context or agent_context.get('memory_context', '')
            available_tools = available_tools or agent_context.get('available_tools', {})
            system_prompt = system_prompt or agent_context.get('system_prompt', '')
            role_prompt = role_prompt or agent_context.get('role_prompt', '')
            user_prompt = user_prompt or agent_context.get('user_prompt', '')
            
            # Format tools information for the prompt
            if isinstance(available_tools, dict):
                # Handle structured tools info from get_available_tools()
                tools_text = self._format_tools_for_prompt(available_tools)
            elif isinstance(available_tools, str):
                # Handle string representation
                tools_text = available_tools
            else:
                # Handle list or other formats
                tools_text = str(available_tools) if available_tools else "No tools available"
            
            # Build comprehensive planning messages
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a task planning expert for AI agents. Create an extensive, detailed, and well structured plan using the following guidelines:\n"
                        "- Format subtask IDs as: main_task_number + letter. Examples: 1a, 1b, 2a, 3a, 5a, 5b, 5c. NOT '5.1' or just 'a'\n"
                        "- Break down the goal into logical main tasks (big objectives)\n"
                        "- Each main task should have specific subtasks (actionable steps)\n"
                        "- Define which tools will be needed for each main task\n"
                        "- Consider the system context and available capabilities\n\n"
                        "- Be extremely concise and informative when writing the decriptions for the Main Task and the Sub Task\n\n"
                        "Important Information:\n\n"
                        "   a. The Observation section of the tasks is for the Agent to record the tool observations. DO NOT WRITE ANYTHING IN THERE.\n\n"
                        "   b. If there is a section of the plan that does not require a tool call, do not populate the predicted_tool_use section of the plan."
                        "   d. When a subtask requires a tool, include the exact tool name in the subtask description (e.g., 'Call episodic_remember to store V1')."
                        "   c. The last section of the plan has to be the formatting task. [If you violate this rule there will be a severe penalty]"
                        "Context: You will be given the Agent's System prompt, the Agent's Role prompt, the Agent's Memory/General Knowledge information, the Agent's Tools, and the Agent's User prompt. "
                        "Your Goal: To deliver an extensive, detailed, and well structured plan to the AI agent. You want to set the agent up for success as best as you possibly can."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a concise todo list that breaks this down into main tasks and subtasks. "
                        "Make sure to define which tools will be needed for each main task based on the available tools. "
                        "Structure it as big main tasks and then the small subtasks to complete each main task. "
                        "Below you will find all of your context needs."
                        f"Agent's Tools: {tools_text}\n"
                        f"Agent's System Prompt: {system_prompt}\n"
                        f"Agent's Memory/General Knowledge information: {memory_context}\n"
                        f"Agent's Role Prompt: {role_prompt}\n"
                        f"Agent's User Prompt: {user_prompt}"
                    )
                }
            ]
            
            # Use instructor to get structured output
            todo_list = self.client.chat.completions.create(
                model="gpt-5",  # Use a reliable model
                messages=messages,
                response_model=TodoList,  # Pass Pydantic model directly
                max_retries=2  # Retry if validation fails
            )
            
            # Return the structured plan as JSON
            return {
                "success": True,
                "plan": todo_list.model_dump(),
                "plan_json": todo_list.model_dump_json(indent=2)
            }
            
        except Exception as e:
            # Fallback to basic task structure if structured planning fails
            return {
                "success": False,
                "error": str(e),
            }
    
    def create_plan_from_agent(self) -> Dict[str, Any]:
        """Create a structured plan using the agent's context."""
        return self.create_structured_plan()
    
# Create a global instance for the tool function
def create_structured_plan(
    memory_context: str = "", 
    available_tools = None,
    role_prompt: str = "",
    system_prompt: str = "",
    user_prompt: str = ""
) -> Dict[str, Any]:
    """
    Function wrapper for the planning tool to be used in agent tool registration.
    
    Args:
        system_prompt: The system prompt providing context and instructions
        user_prompt: The original user prompt/query
        memory_context: Semantic memory context if available
        available_tools: Structured tools info dict, list, or string representation
        role_prompt: The role prompt for the agent
    Returns:
        Dict containing the TodoList as JSON or error information
    """
    _planning_tool = PlanningTool()

    return _planning_tool.create_structured_plan(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        memory_context=memory_context,
        available_tools=available_tools,
        role_prompt=role_prompt,
    )



