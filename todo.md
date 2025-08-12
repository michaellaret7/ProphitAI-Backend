# Filter Out Think Tags from Perplexity Search Output

## Problem Statement
The perplexity free search tool was outputting content that included `<think>` tags with internal thinking processes that should not be shown to users.

## Solution Approach
Add a regex pattern to filter out all content between `<think>` and `</think>` tags, including the tags themselves.

## Todo Items
- [x] 1. Add regex pattern to filter out <think> tags and their content from perplexity search output
- [x] 2. Test the regex to ensure it properly removes all thinking content

## Review

### Changes Made:

1. **Added regex pattern to remove think tags**
   - Added a new regex substitution: `re.sub(r'<think>.*?</think>', '', cleaned_content, flags=re.DOTALL)`
   - Uses non-greedy matching (`.*?`) to properly handle multiple think tag blocks
   - Uses `re.DOTALL` flag to match across multiple lines

2. **Improved code comments**
   - Added clear comments explaining what each regex pattern does
   - Better code documentation for future maintenance

### Technical Details:
- The regex pattern `<think>.*?</think>` matches everything between opening and closing think tags
- The `?` makes it non-greedy, preventing over-matching when multiple think blocks exist
- The `re.DOTALL` flag ensures the pattern works across line breaks

### Result:
The perplexity search output will now be clean, showing only the actual response content without any internal thinking or processing tags.