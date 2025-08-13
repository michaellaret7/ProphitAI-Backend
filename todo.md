# BaseAgent Class Refactoring Plan

## Objective
Break down the BaseAgent class (currently 686 lines) into smaller, more maintainable and modular pieces within a dedicated folder structure, while maintaining all existing functionality.

## Current Structure Analysis
The BaseAgent class contains the following major components:
- Data class: StepTrace
- Initialization and configuration
- Tool registration system
- Core run loop
- Helper methods for various operations
- Message and checklist logging
- Stagnation detection
- JSON/parsing utilities

## Proposed Folder Structure
```
backend/src/agentic_framework/base_agent/
├── __init__.py                    # Export BaseAgent and key components
├── agent.py                        # Main BaseAgent class (core logic)
├── data_models.py                  # StepTrace and other data classes
├── tool_registry.py                # Tool registration and management
├── execution_engine.py             # Core run loop and execution logic
├── helpers/
│   ├── __init__.py
│   ├── message_handler.py         # Message formatting and saving
│   ├── checklist_manager.py       # Checklist tracking functionality
│   ├── stagnation_detector.py     # Stagnation detection logic
│   └── parsing_utils.py           # JSON parsing and text utilities
└── config.py                       # Default configurations and constants
```

## TODO Items

### [x] 1. Create folder structure
- Create `backend/src/agentic_framework/base_agent/` directory
- Create `helpers/` subdirectory
- Create all necessary `__init__.py` files

### [x] 2. Extract data models
- Move `StepTrace` dataclass to `data_models.py`
- Add proper imports and type hints

### [x] 3. Extract tool registry functionality
- Move tool registration methods to `tool_registry.py`
  - `_register_base_tools()`
  - `add_tool()`
  - `_execute_tool_safe()`
- Keep tool function mappings and definitions

### [x] 4. Extract message handling
- Move to `helpers/message_handler.py`:
  - `_save_messages_to_json()`
  - `_save_final_json()`
  - `_system_rules()`
  - Message formatting logic

### [x] 5. Extract checklist management
- Move to `helpers/checklist_manager.py`:
  - `_parse_plan_to_checklist()`
  - `_save_checklist()`
  - `_load_checklist()`
  - `_update_checklist_progress()`
  - `_get_checklist_prompt()`

### [x] 6. Extract stagnation detection
- Move to `helpers/stagnation_detector.py`:
  - `_update_stagnation()`
  - Stagnation tracking variables and logic

### [x] 7. Extract parsing utilities
- Move to `helpers/parsing_utils.py`:
  - `_maybe_parse_json_step()`
  - `_looks_final()`
  - `_extract_last_final()`
  - `_stringify()`

### [x] 8. Create execution engine
- Move core run loop to `execution_engine.py`
- Keep the main `run()` method logic
- Maintain iteration management

### [x] 9. Create configuration module
- Move to `config.py`:
  - Default configurations (max_iterations, stuck_threshold, etc.)
  - File paths for outputs
  - Final keywords list

### [x] 10. Update main agent.py
- Keep only the main BaseAgent class skeleton
- Import all extracted components
- Maintain the same public API
- Ensure __init__ properly initializes all components

### [x] 11. Update imports in dependent files
- Update `cro_agent.py` import
- Update `cio_agent.py` import  
- Update `macro_agent.py` import
- Update `industry_agents.py` import

### [ ] 12. Test functionality
- Verify all agents still work correctly
- Ensure no breaking changes
- Confirm all methods are accessible

## Implementation Notes
- Keep all method signatures exactly the same
- Maintain backward compatibility 
- Use proper imports to keep the same external API
- Ensure the refactored code follows DRY principle
- Keep components loosely coupled for future extensibility

## Review Section
*To be completed after implementation*