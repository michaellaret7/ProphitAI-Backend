# Context Enhancement Plan for Planning Tool

## Overview
Based on the CRO agent messages, we need to provide the planning tool with comprehensive context to create sophisticated, domain-specific plans that match the agent's expertise level.

## Context Categories to Extract and Pass

### 1. **Role-Specific Context**
From the agent messages, extract:
- **Agent Role**: Chief Risk Officer (CRO) for Consumer Staples Fund
- **Core Responsibilities**: Risk assessment, portfolio optimization, correlation analysis
- **Success Metrics**: ~30% net long exposure, 15-20 longs, 10-15 shorts, low beta, high alpha

### 2. **Domain Knowledge Base**
Extract and pass the knowledge base sections:
- **Risk Management Principles**: Covariance matrix, correlation matrix, stress tests
- **Current Date Context**: 2025-08-19 (for market context)
- **Sector Focus**: Consumer Staples Fund specifics

### 3. **Available Tools Context**
Extract detailed tool descriptions with:
- **Portfolio Tools**: stress_test, vol_es, risk_contribution, drawdown_profile, etc.
- **Tool Parameters**: Specific parameter requirements and formats
- **Tool Sequencing**: Optimal tool usage patterns
- **Dictionary Formats**: Exact formatting requirements

### 4. **Execution Framework**
Pass the structured approach:
- **Analysis Phases**: Quantitative baseline → Risk attribution → Historical resilience → Stress testing
- **Iteration Requirements**: Multiple portfolio iterations with full risk analysis
- **Documentation Standards**: Actionable suggestions format
- **Output Requirements**: JSON format with specific structure

## Enhanced Planning Function Parameters

### Current Parameters:
```python
def create_structured_plan(
    goal: str, 
    system_prompt: str, 
    user_prompt: str, 
    memory_context: str = "", 
    available_tools: List[str] = None
) -> Dict[str, Any]
```

### Proposed Enhanced Parameters:
```python
def create_structured_plan(
    goal: str,
    system_prompt: str,
    user_prompt: str,
    memory_context: str = "",
    available_tools: List[Dict[str, Any]] = None,  # Full tool definitions, not just names
    domain_knowledge: str = "",  # Extract knowledge base sections
    execution_framework: str = "",  # Extract execution rules and requirements
    output_requirements: str = "",  # Extract specific output format requirements
    role_context: Dict[str, Any] = None,  # Role-specific context and constraints
    tool_sequencing_rules: str = ""  # Tool usage guidelines and optimal sequences
) -> Dict[str, Any]
```

## Implementation Steps

### Step 1: Context Extraction Function
Create a function in the agent to extract comprehensive context:

```python
def extract_planning_context(self) -> Dict[str, Any]:
    """Extract comprehensive context for planning tool."""
    return {
        "role_context": {
            "role": "Chief Risk Officer (CRO)",
            "domain": "Consumer Staples Fund",
            "constraints": ["15-20 longs", "10-15 shorts", "~30% net exposure"],
            "success_metrics": ["low beta", "high alpha", "risk management"]
        },
        "domain_knowledge": self._extract_knowledge_base(),
        "execution_framework": self._extract_execution_rules(),
        "tool_definitions": self._get_detailed_tool_definitions(),
        "output_requirements": self._extract_output_requirements(),
        "tool_sequencing": self._extract_tool_sequencing_rules()
    }
```

### Step 2: Enhanced Planning Prompt Construction
Build a comprehensive planning prompt that includes:

1. **Agent Identity & Role**
2. **Domain Expertise & Knowledge Base**
3. **Available Tools with Full Descriptions**
4. **Execution Framework & Requirements**
5. **Output Format Specifications**
6. **Tool Sequencing Guidelines**

### Step 3: Contextual Plan Generation
The planning tool should generate plans that:
- **Match the agent's expertise level** (sophisticated financial analysis)
- **Follow domain-specific workflows** (risk assessment → optimization → validation)
- **Use appropriate tool sequences** (vol_es → risk_contribution → stress_test)
- **Meet output requirements** (JSON format with actionable suggestions)
- **Respect constraints** (portfolio rules, analysis requirements)

## Expected Planning Tool Output Enhancement

### Current Output:
Basic main tasks and subtasks

### Enhanced Output:
- **Domain-Specific Main Tasks**: "Establish Quantitative Risk Baseline", "Conduct Risk Attribution Analysis"
- **Technical Subtasks**: "1a: Run vol_es() with default parameters", "1b: Document VaR and ES values"
- **Tool Predictions**: Accurate tool sequences based on domain knowledge
- **Constraint Awareness**: Tasks that ensure compliance with portfolio rules
- **Quality Standards**: Tasks that meet the sophisticated analysis requirements

## Benefits of Enhanced Context

1. **Higher Quality Plans**: Plans that match the agent's expertise level
2. **Domain Accuracy**: Financial terminology and workflows
3. **Tool Optimization**: Proper tool sequencing and usage
4. **Constraint Compliance**: Plans that respect all requirements
5. **Execution Efficiency**: Plans that follow proven workflows

## Next Steps

1. Implement context extraction functions in agent.py
2. Enhance planning tool parameters and prompt construction
3. Test with CRO agent scenarios to validate plan quality
4. Iterate based on plan execution results
