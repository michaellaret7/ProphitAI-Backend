"""Test: Instantiate deferred tools data from all tools and print the catalogue."""

from prophitai_tools.registry import ALL_TOOL_FUNCTIONS
from prophitai_atlas.tools.catalogue import build_deferred_tools_data


def main():
    data = build_deferred_tools_data(ALL_TOOL_FUNCTIONS)

    print("=" * 60)
    print("TOOL REGISTRY (by category)")
    print("=" * 60)
    for category in sorted(data.tool_registry.keys()):
        funcs = data.tool_registry[category]
        print(f"\n[{category}] — {len(funcs)} tools")
        for func in funcs:
            tool = func.tool
            desc = tool.get("description", "").strip().split(".")[0] + "."
            print(f"  - {tool['name']}: {desc}")

    print("\n" + "=" * 60)
    print(f"TOTAL TOOLS: {len(data.all_tools)}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("DEFERRED TOOLS DESCRIPTION")
    print("=" * 60)
    print(data.description)


if __name__ == "__main__":
    main()
