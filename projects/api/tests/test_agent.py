"""Test: Instantiate an Agent with all tools and print the full catalogue."""

from prophitai_tools.registry import ALL_TOOL_FUNCTIONS
from prophitai_atlas.tools.catalogue import ToolCatalogue


def _first_sentence(text: str) -> str:
    """Extract the first sentence from a description string."""
    text = text.strip().replace("\n", " ")
    for i, char in enumerate(text):
        if char == "." and (i + 1 >= len(text) or text[i + 1] in (" ", "\n")):
            return text[: i + 1]
    return text


def main():
    catalogue = ToolCatalogue(ALL_TOOL_FUNCTIONS)

    print("=" * 60)
    print("TOOL REGISTRY (by category)")
    print("=" * 60)
    for category in sorted(catalogue.tool_registry.keys()):
        funcs = catalogue.tool_registry[category]
        print(f"\n[{category}] — {len(funcs)} tools")
        for func in funcs:
            tool = func.tool
            print(f"  - {tool['name']}: {_first_sentence(tool.get('description', ''))}")

    print("\n" + "=" * 60)
    print(f"TOTAL TOOLS: {len(catalogue.all_tools)}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("CATALOGUE PROMPT TEXT")
    print("=" * 60)
    print(catalogue.build_catalogue_description())


if __name__ == "__main__":
    main()
