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
                        "You are a task planning expert for AI agents. Decide task complexity FIRST, then create ACTIONABLE plans.\n\n"

                        "CORE APPROACH:\n"
                        "1) Classify complexity (internally, do NOT include in output): Simple, Moderate, Complex.\n"
                        "2) Shape the plan based on complexity using the rubric below.\n"
                        "3) Tasks are outcomes; Subtasks are action-only execution steps.\n\n"

                        "COMPLEXITY RUBRIC (internal):\n"
                        "- Simple: Narrow scope, 1-2 tools, minimal dependencies, short time horizon.\n"
                        "- Moderate: Broader scope OR multiple tools OR some dependencies/data joins.\n"
                        "- Complex: Multi-stage pipeline, cross-domain, heavy data/backtesting, or strong accuracy constraints.\n\n"

                        "PLANNING GUIDANCE:\n"
                        "- Choose the minimal, sufficient number of tasks and subtasks based on scope, dependencies, and required validation.\n"
                        "- Prefer fewer, high-leverage tasks; add subtasks only for concrete execution steps.\n"
                        "- Avoid meta-work and avoid forcing a fixed task/subtask count.\n\n"

                        "TASKS (WHAT to accomplish):\n"
                        "✓ Outcome-oriented (e.g., 'Screen sector for quality candidates').\n"
                        "✓ Sequenced to minimize dependency churn.\n"
                        "✗ No meta-work like 'Define criteria' or 'List tools'.\n\n"

                        "SUBTASKS (HOW to execute):\n"
                        "✓ Action-only steps that change state or produce artifacts. Start with a verb: 'Fetch', 'Compute', 'Join', 'Run', 'Backtest', 'Generate', 'Validate', 'Summarize'.\n"
                        "✓ Use sparingly; only when the task needs clear execution steps.\n"
                        "✗ No thinking-only items (e.g., 'Brainstorm', 'Consider', 'Reflect').\n"
                        "✗ No restating the task or adding meta-instructions.\n\n"

                        "FORMAT REQUIREMENTS:\n"
                        "- Main tasks use integer ids starting at 1.\n"
                        "- Subtasks use number+letter ids (e.g., '1a', '2b').\n"
                        "- Descriptions are concise, imperative, outcome-focused.\n\n"

                        "EXAMPLES:\n\n"
                        "Request: 'Summarize Q3 earnings call transcript' → Simple\n"
                        "Task 1: Extract and synthesize key points\n"
                        "  Subtask 1a: Fetch transcript\n"
                        "  Subtask 1b: Segment and summarize sections\n"
                        "  Subtask 1c: Generate bullet summary\n\n"
                        "Request: 'Pick top 2 automobile stocks' → Simple\n"
                        "Task 1: Screen automobile sector for quality candidates\n"
                        "Task 2: Analyze top candidates and select best 2 with thesis\n"
                        "[2 tasks; subtasks only if needed for execution]\n\n"

                        "Request: 'Analyze energy sector and build portfolio' → Moderate\n"
                        "Task 1: Screen energy sector for candidates\n"
                        "Task 2: Analyze fundamentals (quality, valuation, growth)\n"
                        "  Subtask 2a: Compute ROIC/margins/FCF\n"
                        "  Subtask 2b: Compute valuation (P/E, EV/EBITDA)\n"
                        "Task 3: Select picks and size positions\n\n"

                        "Request: 'Backtest and optimize multi-factor long/short strategy' → Complex\n"
                        "Task 1: Gather and align factor datasets\n"
                        "  Subtask 1a: Fetch historical prices and fundamentals\n"
                        "  Subtask 1b: Join and clean panel data\n"
                        "Task 2: Build and run baseline backtest\n"
                        "  Subtask 2a: Generate signals and weights\n"
                        "  Subtask 2b: Execute backtest with costs and constraints\n"
                        "Task 3: Optimize and validate\n"
                        "  Subtask 3a: Parameter sweep and select best config\n"
                        "  Subtask 3b: Robustness checks and diagnostics\n\n"

                        "REMEMBER:\n"
                        "- Decide complexity first (internally).\n"
                        "- Prefer the fewest tasks that fully execute the work.\n"
                        "- Subtasks are for execution, not thinking."
                        "- Important Rule: The final answer output/formatting should be extremely concise and to the point. Make it one subtask like this for example: "
                        "    - Subtask a: Output the final answer in the format specified by the user. Do not add any other text or commentary."
                        "    - The final output may only contain one subtask like this. (violating this rule will result in serious consequences)"
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a TodoList whose scope matches the task's complexity (decide internally; do NOT output the label).\n\n"

                        f"INSTRUCTIONS:\n"
                        f"1. Decide complexity internally (Simple, Moderate, Complex) using the rubric.\n"
                        f"2. Choose the minimal set of tasks to fully execute the request; do not target a fixed count.\n"
                        f"3. Use subtasks only for concrete, action-only steps (start with a verb).\n"
                        f"4. IDs: tasks start at 1; subtasks are number+letter (e.g., '1a').\n"
                        f"5. Output only the structured TodoList (no commentary).\n\n"

                        f"CONTEXT:\n\n"
                        f"User Request: {user_prompt}\n\n"
                        f"Agent Role: {role_prompt}\n\n"
                        f"System Context: {system_prompt}\n\n"
                        f"Available Tools: {tools_text}\n\n"

                        f"Create the minimal-but-complete plan for the chosen complexity."
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



