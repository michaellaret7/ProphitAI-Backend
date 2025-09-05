"""Semantic memory system for agent-specific knowledge and insights."""

import json
import textwrap
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


class SemanticMemory:
    """Manages semantic memories for specialized agent knowledge."""
    
    def __init__(self, agent_type: str, save_memory: bool = True, verbose: bool = False):
        """Initialize semantic memory for a specific agent type.
        
        Args:
            agent_type: Type of agent (e.g., 'cro', 'macro', 'industry')
            save_memory: Whether to persist memory to disk
            verbose: Whether to print debug messages
        """
        self.agent_type = agent_type.lower()
        self.save_memory = save_memory
        self.verbose = verbose
        
        # Memory storage path - each agent type has its own file
        self.memory_dir = Path(__file__).parent / "memory_store" / "semantic_memory"
        if self.agent_type == "beverages":
            self.memory_path = self.memory_dir / "consumer_staples_fund" / f"{self.agent_type}_memory.json"
        else:
            self.memory_path = self.memory_dir / f"{self.agent_type}_memory.json"
        
        # In-memory storage
        self.memories: Dict[str, List[Dict[str, Any]]] = {}
        
        # Load existing memories
        if self.save_memory:
            self._load_memories()
    
    def _load_memories(self) -> None:
        """Load semantic memories from disk."""
        try:
            if self.memory_path.exists():
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Require the unified structure
                    if 'agent_memory' not in data:
                        raise ValueError(f"Memory file {self.memory_path} does not follow the unified structure. Expected 'agent_memory' root key.")
                    
                    agent_data = data['agent_memory']
                    
                    # Store agent info
                    self.memory_type = agent_data.get('type', 'Semantic')
                    self.agent_name = agent_data.get('agent', self.agent_type)
                    self.domain = agent_data.get('domain', '')
                    self.purpose = agent_data.get('purpose', '')
                    self.last_updated = agent_data.get('last_updated', '')
                    
                    # Load memories (which now contains tickers and sections/categories)
                    if 'memories' in agent_data:
                        memories_data = agent_data['memories']
                        
                        # Extract tickers if present
                        if 'tickers' in memories_data:
                            self.tickers = memories_data['tickers']
                        
                        # Extract industry if present
                        if 'industry' in memories_data:
                            self.industry = memories_data['industry']
                        
                        # Load actual memory categories (sections, risk_management, etc.)
                        self.memories = {k: v for k, v in memories_data.items() if k not in ['tickers', 'industry']}
                    else:
                        self.memories = {}
                    
                    # Update current date
                    self._update_current_date_in_memory(data)
                    
                    if self.verbose:
                        total_memories = sum(len(m) for m in self.memories.values())
                        print(f"📚 Loaded {total_memories} semantic memories for {self.agent_type} agent")

        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load semantic memory: {e}")
            self.memories = {}
    
    def _update_current_date_in_memory(self, data: Dict[str, Any]) -> None:
        """Update the current_date and last_updated fields in memory with today's date."""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if 'agent_memory' not in data:
            return
            
        agent_data = data['agent_memory']
        updated = False
        
        # Update current_date if present
        if 'current_date' in agent_data:
            agent_data['current_date'] = current_date
            updated = True
            
        # Always update last_updated
        if 'last_updated' in agent_data:
            agent_data['last_updated'] = current_date
            updated = True
            
        # Save the updated memory back to disk if save_memory is enabled
        if updated and self.save_memory:
            try:
                self.memory_dir.mkdir(parents=True, exist_ok=True)
                with open(self.memory_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                if self.verbose:
                    print(f"📅 Updated dates to {current_date} in {self.agent_type} memory")
                    
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Failed to save updated dates: {e}")
    
    def _save_memories(self) -> None:
        """Save semantic memories to disk in unified format."""
        if not self.save_memory:
            return
            
        try:
            # Ensure directory exists
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Build memories dict with tickers and industry first if present
            memories_dict = {}
            if hasattr(self, 'tickers') and self.tickers:
                memories_dict['tickers'] = self.tickers
            if hasattr(self, 'industry') and self.industry:
                memories_dict['industry'] = self.industry
            memories_dict.update(self.memories)
            
            # Build the unified structure
            data = {
                'agent_memory': {
                    'type': getattr(self, 'memory_type', 'Semantic'),
                    'agent': getattr(self, 'agent_name', self.agent_type),
                    'domain': getattr(self, 'domain', ''),
                    'purpose': getattr(self, 'purpose', ''),
                    'last_updated': datetime.now().strftime('%Y-%m-%d'),
                    'memories': memories_dict
                }
            }
            
            # Add current_date if it was present originally
            if hasattr(self, 'current_date'):
                data['agent_memory']['current_date'] = self.current_date
            
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            if self.verbose:
                total_memories = sum(len(m) for m in self.memories.values())
                print(f"💾 Saved {total_memories} semantic memories for {self.agent_type} agent")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save semantic memory: {e}")
    
    def add_memory(self, category: str, memory: Dict[str, Any]) -> None:
        """Add a semantic memory to a category.
        
        Args:
            category: Category of memory (e.g., 'risk_management', 'portfolio_construction')
            memory: Memory content with title, content, keywords, etc.
        """
        if category not in self.memories:
            self.memories[category] = []
        
        # Add timestamp if not present
        if 'created_at' not in memory:
            memory['created_at'] = datetime.now().isoformat()
        
        # Ensure memory has required fields
        if 'title' not in memory:
            memory['title'] = f"Memory_{len(self.memories[category])}"
        if 'keywords' not in memory:
            memory['keywords'] = []
        
        self.memories[category].append(memory)
        self._save_memories()
        
        if self.verbose:
            print(f"➕ Added memory to {category}: {memory.get('title')}")
    
    def get_memories_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all memories in a specific category.
        
        Args:
            category: Category to retrieve
            
        Returns:
            List of memories in that category
        """
        return self.memories.get(category, [])
    
    def get_memories_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Get memories matching any of the provided keywords.
        
        Args:
            keywords: List of keywords to search for
            
        Returns:
            List of matching memories
        """
        matching_memories = []
        keywords_lower = [k.lower() for k in keywords]
        
        for category, memories in self.memories.items():
            for memory in memories:
                memory_keywords = [k.lower() for k in memory.get('keywords', [])]
                # Check if any keyword matches
                if any(kw in memory_keywords for kw in keywords_lower):
                    matching_memories.append({
                        'category': category,
                        **memory
                    })
        
        return matching_memories
    
    def get_all_memories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all memories organized by category.
        
        Returns:
            Dict of all memories by category
        """
        return self.memories
    
    def _extract_field(self, memory: Dict[str, Any], field_type: str) -> Any:
        """Extract a field from memory with flexible field name matching.
        
        Args:
            memory: Memory dict with various field names
            field_type: Type of field to extract ('title', 'content', 'application', 'metrics')
            
        Returns:
            Extracted field value or default
        """
        field_mappings = {
            'title': ['title', 'topic', 'name', 'subject', 'heading'],
            'content': ['content', 'context', 'description', 'details', 'text'],
            'application': ['application', 'investment_insight', 'investment_angle', 
                          'strategic_implications', 'investment_implications', 
                          'expansion_success_factors', 'critical_metrics_to_monitor',
                          'key_monitoring_points', 'hedging_analysis', 'roi_notes', 
                          'esg_metrics'],
            'additional': ['additional_notes', 'notes', 'comments'],
            'metrics': ['metrics_structured', 'metrics', 'metrics_raw']
        }
        
        # Try each possible field name
        for field_name in field_mappings.get(field_type, []):
            if field_name in memory:
                value = memory[field_name]
                # Handle list values for application/additional fields
                if field_type in ['application', 'additional'] and isinstance(value, list):
                    return ' | '.join(value) if len(value) <= 3 else '\n• ' + '\n• '.join(value)
                return value
        
        # Return defaults
        if field_type == 'title':
            return f"Item {memory.get('id', 'Unknown')}"
        return ""
    
    def _humanize_key(self, key: Any) -> str:
        """Convert a key into a human-friendly label without relying on schema."""
        try:
            text = str(key).replace('_', ' ').strip()
            if not text:
                return "Key"
            return text[0].upper() + text[1:]
        except Exception:
            return str(key)
    
    def _stringify_value(self, value: Any) -> str:
        """Safely stringify scalar values for display."""
        if value is None:
            return "None"
        if isinstance(value, float):
            # Keep simple, avoid scientific unless very small/large
            return ("%.6f" % value).rstrip('0').rstrip('.')
        return str(value)
    
    def _format_generic(self, obj: Any, indent_level: int = 0, parent_key: str = "") -> List[str]:
        """Schema-agnostic pretty-printer for dicts/lists/scalars.
        Formats data cleanly for LLM consumption.
        """
        lines: List[str] = []
        indent = "  " * indent_level
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                label = self._humanize_key(key)
                
                # Skip category field as it's redundant
                if key == 'category':
                    continue
                    
                if isinstance(value, (dict, list)):
                    # For nested structures, add header and recurse
                    lines.append("")
                    lines.append(f"{indent}{label}:")
                    lines.extend(self._format_generic(value, indent_level + 1, key))
                else:
                    # For scalar values, format inline
                    string_value = self._stringify_value(value)
                    
                    # Long text gets paragraph formatting
                    if isinstance(value, str) and len(string_value) > 80:
                        lines.append("")
                        lines.append(f"{indent}{label}:")
                        # Wrap text nicely
                        wrapper = textwrap.TextWrapper(
                            width=100,
                            initial_indent=f"{indent}  ",
                            subsequent_indent=f"{indent}  ",
                            break_long_words=False,
                            break_on_hyphens=False
                        )
                        wrapped_lines = wrapper.wrap(string_value)
                        lines.extend(wrapped_lines)
                    else:
                        # Short values stay inline
                        lines.append(f"{indent}{label}: {string_value}")
            
            return lines
        
        if isinstance(obj, list):
            if not obj:
                return []
            
            # Check if it's a list of complex objects or simple values
            all_dicts = all(isinstance(item, dict) for item in obj)
            all_strings = all(isinstance(item, str) for item in obj)
            
            if all_dicts:
                # Format each dict item with spacing
                for i, item in enumerate(obj, 1):
                    if i > 1:
                        lines.append("")  # Space between items
                    lines.extend(self._format_generic(item, indent_level))
            elif all_strings and len(obj) > 1:
                # Bullet list for multiple strings
                for item in obj:
                    if len(item) > 80:
                        # Long string gets wrapped
                        wrapper = textwrap.TextWrapper(
                            width=100,
                            initial_indent=f"{indent}• ",
                            subsequent_indent=f"{indent}  ",
                            break_long_words=False,
                            break_on_hyphens=False
                        )
                        lines.extend(wrapper.wrap(item))
                    else:
                        lines.append(f"{indent}• {item}")
            else:
                # Mixed or single items
                for item in obj:
                    if isinstance(item, (dict, list)):
                        lines.extend(self._format_generic(item, indent_level))
                    else:
                        lines.append(f"{indent}• {self._stringify_value(item)}")
            
            return lines
        
        # Scalar values
        string_value = self._stringify_value(obj)
        if len(string_value) > 100:
            wrapper = textwrap.TextWrapper(
                width=100,
                initial_indent=indent,
                subsequent_indent=indent,
                break_long_words=False,
                break_on_hyphens=False
            )
            lines.extend(wrapper.wrap(string_value))
        else:
            lines.append(f"{indent}{string_value}")
        
        return lines
    
    def format_memories_for_prompt(self, categories: List[str] = None, 
                                  keywords: List[str] = None,
                                  concise: bool = False) -> str:
        """Format relevant memories as context for the agent prompt.
        
        Args:
            categories: Optional list of categories to include
            keywords: Optional list of keywords to filter by
            concise: If True, format in a more compact way for refresh injections
            
        Returns:
            Formatted string of relevant memories
        """
        relevant_memories = []
        
        # Get memories by category
        if categories:
            for category in categories:
                for memory in self.get_memories_by_category(category):
                    relevant_memories.append({
                        'category': category,
                        **memory
                    })
        
        # Get memories by keywords
        if keywords:
            keyword_memories = self.get_memories_by_keywords(keywords)
            # Avoid duplicates
            for km in keyword_memories:
                if km not in relevant_memories:
                    relevant_memories.append(km)
        
        # If no filters, get all
        if not categories and not keywords:
            for category, memories in self.memories.items():
                for memory in memories:
                    relevant_memories.append({
                        'category': category,
                        **memory
                    })
        
        if not relevant_memories:
            return ""
        
        # Group memories back by category for robust rendering
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for mem in relevant_memories:
            cat = mem.get('category', 'general')
            # Avoid duplicating the helper key inside the payload
            payload = {k: v for k, v in mem.items() if k != 'category'}
            grouped.setdefault(cat, []).append(payload)
        
        # Format as context
        if concise:
            formatted = []
            current_date = self.get_current_date()
            if current_date:
                formatted.append(f"Date: {current_date}")
            for category, items in grouped.items():
                formatted.append(f"- [{category.upper()}] {len(items)} item(s)")
            return "\n".join(formatted)
        
        # Full format for initial context
        formatted = ["RELEVANT KNOWLEDGE BASE"]
        formatted.append("=" * 50)
        
        # Add current date at the top of knowledge base
        current_date = self.get_current_date()
        if current_date:
            formatted.append(f"\nCURRENT DATE: {current_date}")
            formatted.append("")
        
        # Include industry if present
        if hasattr(self, 'industry') and self.industry:
            formatted.append(f"Industry: {self.industry}")
            formatted.append("")
        
        # Include tickers if present
        if hasattr(self, 'tickers') and self.tickers:
            formatted.append("Tickers")
            formatted.extend(self._format_generic(self.tickers, indent_level=1))
            formatted.append("")
        
        for category, items in grouped.items():
            formatted.append("")
            formatted.append(f"[{category.upper()}]")
            formatted.append("-" * 50)
            
            for idx, item in enumerate(items, start=1):
                formatted.append(f"\n{idx}. Memory Item")
                formatted.extend(self._format_generic(item, indent_level=1))
                
                # Add separator between items if not last
                if idx < len(items):
                    formatted.append("\n" + "." * 30)
        
        formatted.append("=" * 50)
        formatted.append("Use the above knowledge to inform your analysis and decisions.")
        
        return "\n".join(formatted)
    
    def get_current_date(self) -> Optional[str]:
        """Get the current date from memory if available."""
        # Check if we have the date stored in our loaded data
        if self.save_memory and self.memory_path.exists():
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'agent_memory' in data:
                        agent_data = data['agent_memory']
                        # Prefer current_date, fallback to last_updated
                        return agent_data.get('current_date') or agent_data.get('last_updated')
            except Exception:
                pass
        
        # Fallback to current system date
        return datetime.now().strftime('%Y-%m-%d')






