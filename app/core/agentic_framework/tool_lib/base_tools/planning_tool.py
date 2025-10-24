"""Planning tool for creating structured task plans using Pydantic models."""

import instructor
from openai import OpenAI
from typing import Dict, Any
from dotenv import load_dotenv

# Import from V2 (avoid circular dependency with V1)
try:
    from app.core.agentic_framework.base_agent_v2.tasks.models import TodoList, MainTask, SubTask, TaskStatus
except ImportError:
    # Fallback to V1 if V2 not available (backwards compatibility)
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
        
        # Extract domain memory context
        if hasattr(self.agent, 'domain_memory') and self.agent.domain_memory:
            context['memory_context'] = self.agent.domain_memory.format_memories_for_prompt(concise=True)
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
            memory_context: Domain memory context if available
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
                        "You are a task planning expert for AI agents. Create SIMPLE, ACTIONABLE plans.\n\n"

                        "CORE PHILOSOPHY:\n"
                        "Favor simplicity and speed. Create the MINIMUM structure needed. Let the agent figure out details.\n\n"

                        "PLANNING RULES:\n\n"

                        "1. DEFAULT TO SIMPLE PLANS\n"
                        "   - Stock screening/picks: 2-3 tasks MAX, 0-2 subtasks per task\n"
                        "   - Analysis/research: 3-4 tasks MAX, 1-3 subtasks per task  \n"
                        "   - Complex multi-step: 4-5 tasks MAX, 2-4 subtasks per task\n"
                        "   NEVER exceed 5 main tasks unless explicitly requested.\n\n"

                        "2. TASKS = HIGH-LEVEL OBJECTIVES (What to accomplish)\n"
                        "   ✓ 'Screen candidates for quality and growth'\n"
                        "   ✓ 'Analyze top 3-5 candidates and select best 2'\n"
                        "   ✓ 'Create investment thesis and risk assessment'\n"
                        "   X 'Compile comprehensive list' ← Too granular\n"
                        "   X 'Segment by sub-industry' ← Too granular\n"
                        "   X 'Apply investability filters' ← Too granular\n\n"

                        "3. SUBTASKS = ONLY IF NEEDED\n"
                        "   Only create subtasks if the main task is complex:\n"
                        "   - Most tasks need 0-2 subtasks\n"
                        "   - Only use subtasks for genuinely distinct analytical steps\n"
                        "   - Agent has full autonomy to gather data within each task\n\n"

                        "4. TRUST THE AGENT\n"
                        "   The agent has tools and can:\n"
                        "   - Figure out what data to gather\n"
                        "   - Decide which metrics to analyze\n"
                        "   - Determine when a task is complete\n"
                        "   Don't over-specify or over-structure.\n\n"

                        "ANTI-PATTERNS (what NOT to do):\n"
                        "X Too many tasks (>5 for simple requests)\n"
                        "X Tasks for meta-work ('Define criteria', 'List tools')\n"
                        "X Tasks as tool calls ('Call stock_screener')\n"
                        "X Too many subtasks (agent can figure it out)\n\n"

                        "EXAMPLES:\n\n"

                        "Request: 'Pick top 2 automobile stocks'\n"
                        "GOOD (simple, actionable):\n"
                        "Task 1: Screen automobile sector for quality candidates (strong margins, FCF, growth)\n"
                        "Task 2: Analyze top candidates and select best 2 with investment thesis\n"
                        "[2 tasks, 0 subtasks - agent figures out details]\n\n"

                        "BAD (over-planning):\n"
                        "Task 1: Assemble investable universe\n"
                        "  Subtask 1a: Compile comprehensive list\n"
                        "  Subtask 1b: Segment by sub-industry\n"
                        "  Subtask 1c: Apply filters\n"
                        "Task 2: Screen for quality...\n"
                        "[Problem: 7 tasks, 19 subtasks for a simple request!]\n\n"

                        "Request: 'Analyze energy sector and build portfolio'\n"
                        "GOOD (balanced):\n"
                        "Task 1: Screen energy sector for candidates\n"
                        "Task 2: Analyze fundamentals (quality, valuation, growth)\n"
                        "  Subtask 2a: Quality metrics (ROIC, margins, FCF)\n"
                        "  Subtask 2b: Valuation metrics (P/E, EV/EBITDA)\n"
                        "Task 3: Select top picks and create portfolio with position sizing\n"
                        "[3 tasks, 2 subtasks - balanced structure]\n\n"

                        "REMEMBER:\n"
                        "- Keep it SIMPLE - agent can handle complexity\n"
                        "- 2-4 tasks is usually enough\n"
                        "- Subtasks only if genuinely needed\n"
                        "- Trust the agent's judgment"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a SIMPLE, MINIMAL TodoList for the user's request.\n\n"

                        f"INSTRUCTIONS:\n"
                        f"1. Create 2-3 tasks MAX (only add more if truly necessary)\n"
                        f"2. Keep subtasks to minimum (0-2 per task)\n"
                        f"3. Make tasks actionable and high-level\n"
                        f"4. Trust the agent to figure out details\n\n"

                        f"CONTEXT:\n\n"
                        f"User Request: {user_prompt}\n\n"
                        f"Agent Role: {role_prompt}\n\n"
                        f"System Context: {system_prompt}\n\n"
                        f"Available Tools: {tools_text}\n\n"

                        f"Create the SIMPLEST plan that accomplishes the goal. Favor brevity over comprehensiveness."
                    )
                }
            ]
            
            # Use instructor to get structured output
            todo_list = self.client.chat.completions.create(
                model="gpt-5-mini",  # Use a reliable model
                messages=messages,
                response_model=TodoList,  # Pass Pydantic model directly
                max_retries=2,  # Retry if validation fails
                reasoning_effort="high"
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
        memory_context: Domain memory context if available
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



