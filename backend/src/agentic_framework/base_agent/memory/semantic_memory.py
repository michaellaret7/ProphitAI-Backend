"""Semantic memory system for agent-specific knowledge and insights."""

import json
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
                    loaded_memories: Dict[str, List[Dict[str, Any]]] = {}
                    if isinstance(data, dict):
                        # Primary schema: { "memories": { <category>: [ ... ] } }
                        if isinstance(data.get('memories'), dict):
                            loaded_memories = data['memories']
                        else:
                            # Alternate schema: top-level categories only, e.g. { "risk_management": [ ... ] }
                            top_level_categories = {
                                key: value for key, value in data.items() if isinstance(value, list)
                            }
                            if top_level_categories:
                                loaded_memories = top_level_categories
                    self.memories = loaded_memories
                    
                    # Dynamically inject current date into memory
                    self._update_current_date_in_memory(data)
                    
                    if self.verbose:
                        total_memories = sum(len(m) for m in self.memories.values())
                        print(f"📚 Loaded {total_memories} semantic memories for {self.agent_type} agent")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load semantic memory: {e}")
            self.memories = {}
    
    def _update_current_date_in_memory(self, data: Dict[str, Any]) -> None:
        """Update the current_date field in memory with today's date."""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if current_date field exists and update it
        if isinstance(data, dict) and 'current_date' in data:
            data['current_date'] = current_date
            
            # Save the updated memory back to disk if save_memory is enabled
            if self.save_memory:
                try:
                    self.memory_dir.mkdir(parents=True, exist_ok=True)
                    with open(self.memory_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    if self.verbose:
                        print(f"📅 Updated current_date to {current_date} in {self.agent_type} memory")
                        
                except Exception as e:
                    if self.verbose:
                        print(f"⚠️ Failed to save updated current_date: {e}")
    
    def _save_memories(self) -> None:
        """Save semantic memories to disk."""
        if not self.save_memory:
            return
            
        try:
            # Ensure directory exists
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                'agent_type': self.agent_type,
                'memories': self.memories,
                'last_updated': datetime.now().isoformat()
            }
            
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
        
        # Format as context
        if concise:
            # Concise format for refresh injections
            formatted = []
            
            # Add current date for context
            current_date = self.get_current_date()
            if current_date:
                formatted.append(f"📅 Date: {current_date}")
                
            for memory in relevant_memories:
                title = memory.get('title', 'Untitled')
                key_point = memory.get('application') or memory.get('content', '')[:150]
                formatted.append(f"• {title}: {key_point}")
            return "\n".join(formatted)
        else:
            # Full format for initial context
            formatted = ["📚 RELEVANT KNOWLEDGE BASE:"]
            formatted.append("=" * 50)
            
            # Add current date at the top of knowledge base
            current_date = self.get_current_date()
            if current_date:
                formatted.append(f"\n📅 CURRENT DATE: {current_date}")
                formatted.append("")
            
            for memory in relevant_memories:
                formatted.append(f"\n[{memory.get('category', 'general').upper()}] {memory.get('title', 'Untitled')}")
                formatted.append(f"{memory.get('content', '')}")
                if memory.get('application'):
                    formatted.append(f"→ Application: {memory['application']}")
                formatted.append("")
            
            formatted.append("=" * 50)
            formatted.append("Use the above knowledge to inform your analysis and decisions.\n")
            
            return "\n".join(formatted)
    
    def get_current_date(self) -> Optional[str]:
        """Get the current date from memory if available."""
        # First check if we have the date stored at the root level of our loaded data
        if self.save_memory and self.memory_path.exists():
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('current_date')
            except Exception:
                pass
        
        # Fallback to current system date
        return datetime.now().strftime('%Y-%m-%d')


# Pre-populate CRO Agent risk management concepts
def initialize_cro_memories():
    """Initialize CRO agent with essential risk management concepts."""
    memory = SemanticMemory(agent_type='cro', save_memory=True, verbose=False)
    
    # 1. Correlation Risk Management
    # memory.add_memory(
    #     category='risk_management',
    #     memory={
    #         'title': 'Correlation Risk and Diversification',
    #         'content': (
    #             'Portfolio correlation is a hidden risk that manifests during market stress. '
    #             'Assets that appear uncorrelated in normal markets often become highly correlated '
    #             'during crises. To manage this: (1) Limit sector concentration to max 30% in any '
    #             'single industry, (2) Balance long/short positions to reduce directional risk, '
    #             '(3) Include defensive positions that benefit from volatility or market declines.'
    #         ),
    #         'keywords': ['correlation', 'diversification', 'concentration', 'crisis'],
    #         'application': 'When constructing portfolios, actively check correlation matrices and ensure true diversification across factors, not just tickers.',
    #         'priority': 'critical'
    #     }
    # )
    
    return memory
