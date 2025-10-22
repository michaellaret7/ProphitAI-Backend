# [Project Name] Planning Document

**Date:** YYYY-MM-DD
**Status:** [Draft / Ready for Implementation / In Progress / Complete]
**Priority:** [Low / Medium / High / Critical]

---

## SECTION 1: OVERALL ANALYSIS & DIAGNOSIS

### Executive Summary

**Brief overview of the problem/opportunity (2-3 paragraphs)**
- What is being addressed?
- Why is it important?
- What is the scope?

**Critical Metrics:**
- Metric 1: Current state → Target state
- Metric 2: Current state → Target state
- Metric 3: Current state → Target state
- Estimated impact: [quantify improvements]

### Component-by-Component Analysis

#### 1. [Component Name] (Current State Metrics)

**Current State:**
- **Section 1**: Description and line numbers/scope
- **Section 2**: Description and line numbers/scope
- **Section 3**: Description and line numbers/scope

**Issues Identified:**

1. **[Issue Category 1]**
   - Specific problem description
   - Location/scope
   - Impact on system
   - Code examples if relevant

2. **[Issue Category 2]**
   - Specific problem description
   - Location/scope
   - Impact on system
   - Code examples if relevant

3. **[Additional Issues]**
   - Continue as needed...

#### 2. [Additional Components]
- Follow same structure for each component being analyzed

### Cross-Cutting Concerns Analysis

#### [Concern 1: e.g., Code Duplication]

1. **[Specific Instance 1]**
   ```language
   # Example code or description
   ```

2. **[Specific Instance 2]**
   ```language
   # Example code or description
   ```

**Impact**: How this affects the system

#### [Additional Cross-Cutting Concerns]
- Repeat pattern as needed

### Design Principle Violations Summary

#### [Principle 1: e.g., KISS] - **GRADE: [A-F]**

**Violations:**
1. **[Specific violation with location]**
2. **[Additional violations]**

**Impact:**
- Concrete consequences of violations
- Developer productivity impact
- Maintenance burden

#### [Additional Principles]
- YAGNI - Grade and violations
- DRY - Grade and violations
- Single Responsibility - Grade and violations
- Dependency Inversion - Grade and violations

### Root Causes

Why did these issues accumulate?
1. **[Root Cause 1]**: Explanation
2. **[Root Cause 2]**: Explanation
3. **[Root Cause 3]**: Explanation

### Impact on Development

**Current State Problems:**
- Problem 1: Specific metric/time impact
- Problem 2: Specific metric/time impact
- Problem 3: Specific metric/time impact

**After Changes:**
- Improvement 1: Expected metric/time improvement
- Improvement 2: Expected metric/time improvement
- Improvement 3: Expected metric/time improvement

### Proposed Metrics for Success

| Metric | Before | Target | Success Criteria |
|--------|--------|--------|------------------|
| **[Metric 1]** | Current value | Target value | Definition of success |
| **[Metric 2]** | Current value | Target value | Definition of success |
| **[Metric 3]** | Current value | Target value | Definition of success |

---

## SECTION 2: PHASED IMPLEMENTATION PLAN

### Overview

The implementation will be done in [N] phases:
1. **Phase 1**: [Brief description] - [No/minimal] breaking changes
2. **Phase 2**: [Brief description]
3. **Phase 3**: [Brief description]
4. **Phase N**: [Final phase description]

**Key Principle**: [Overall implementation strategy - e.g., "Build new, switch atomically, delete old"]

### Phase 1: [Phase Name] (Duration: [Time Estimate])

**Goal**: [Clear goal statement - what will be accomplished in this phase]

#### 1.1: [Sub-task Name]
**What**: [What is being done]
**Files**: [List of files created/modified/deleted]
**Checklist**:
- [ ] Specific action item 1
- [ ] Specific action item 2
- [ ] Specific action item 3
  - [ ] Sub-item if needed
- [ ] Final verification step

**Validation**: [How to verify this sub-task is complete]

#### 1.2: [Additional Sub-tasks]
- Follow same structure

**Phase 1 Complete**: [Final validation criteria for entire phase]

---

### Phase 2: [Phase Name] (Duration: [Time Estimate])

**Goal**: [Clear goal statement]

#### 2.1: [Sub-task Name]
**What**: [Description]
**Files**: [Files affected]
**Checklist**:
- [ ] Action items with specific code changes when possible:
  ```language
  # OLD (line numbers)
  old_code_example

  # NEW
  new_code_example
  ```
- [ ] Additional items

**Validation**: [Verification criteria]

#### 2.2: [Additional Sub-tasks]
- Continue pattern

**Phase 2 Complete**: [Final validation criteria]

---

### Phase 3-N: [Continue Pattern]

- Follow same structure for all remaining phases
- Each phase should have:
  - Clear goal
  - Numbered sub-tasks
  - Detailed checklists
  - Validation criteria
  - Completion criteria

---

## SECTION 3: DETAILED EXECUTION GUIDES

This section provides step-by-step instructions for key tasks with exact code, files, and techniques.

### GUIDE [X.Y]: [Guide Name]

**Context**: [Why this guide exists, what problem it solves, background information]

**Files to Create/Modify**:
1. `path/to/file1.ext`
2. `path/to/file2.ext`
3. `path/to/fileN.ext`

#### Execution Steps

**Step 1**: [Action description]
```language
# Exact code or command to execute
```

**Step 2**: [Next action]
```language
# Code example
```

**Step 3**: [Continue pattern]
- Detailed explanation if needed
- Multiple code blocks if necessary

**Step 4**: [Verification]
```language
# How to verify this worked
```

---

### GUIDE [X.Y]: [Additional Guides]

- Create as many detailed guides as needed for complex tasks
- Each guide should be self-contained
- Include context, exact code, and verification steps

---

## SECTION 4: NEW [SYSTEM/COMPONENT] STRUCTURE

This section visualizes the before/after structure of the system after all implementation phases are complete.

### Current Structure (Before Changes)

```
[Visual representation of current structure]
directory/
├── file1.ext                    ([size]) [status emoji]
├── file2.ext                    ([size]) [status emoji]
│
├── subfolder/
│   ├── file3.ext                ([size]) [status emoji]
│   └── file4.ext                ([size]) [status emoji]
│
└── problematic_folder/           ⚠️ [Note about issues]
    └── bad_file.ext              ([size]) ❌ [Problem description]

TOTALS:
- Total Files: [N] files
- Files With Issues: [N] files
- [Other relevant metrics]
- Compliance Rate: [X]%
```

### New Structure (After Changes)

```
[Visual representation of new structure]
directory/
├── file1.ext                    ([size]) ✅ [Note about improvements]
├── file2.ext                    ([size]) ✅
│
├── new_folder/                   ✨ NEW - [Purpose]
│   ├── new_file1.ext            ([size]) ✅ [Description]
│   └── new_file2.ext            ([size]) ✅ [Description]
│
├── improved_folder/
│   ├── refactored_file.ext      ([size]) ✅ [Improvements]
│   └── file4.ext                ([size]) ✅
│
└── utils/
    └── helper.ext               ([size]) ✅

TOTALS:
- Total Files: [N] files
- Files With Issues: 0 files ✅
- [Other relevant metrics]
- Compliance Rate: 100% ✅
```

### Comparison Table

| Component | Before | After | Change | Status |
|-----------|--------|-------|--------|--------|
| **[Component 1]** | [metric] | [metric] | **[change] ([%])** | ✅ [Description] |
| **[Component 2]** | [metric] | [metric] | **[change] ([%])** | ✅ [Description] |
| **[Component N]** | [metric] | [metric] | **[change] ([%])** | ✅ [Description] |
| **NEW: [Component]** | 0 | [metric] | +[amount] | ✅ [Purpose] |
| **DELETED: [Component]** | [metric] | 0 | -[amount] | ✅ [Reason] |
| **Net Change** | **[total before]** | **[total after]** | **[total change] ([%])** | **✅ SUCCESS** |

### Architecture Visualization

#### Before: [Current State Description]

```
┌────────────────────────────────────────────────────┐
│                  [Component Name]                   │
│                   ([metrics])                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ • [Responsibility 1]                         │  │
│  │ • [Responsibility 2]                         │  │
│  │ • [Problem description]                      │  │
│  └──────────────────────────────────────────────┘  │
│                      │ │                            │
│         ┌────────────┘ └────────────┐              │
│         ▼                            ▼              │
│  ┌──────────────┐            ┌──────────────┐      │
│  │ [Component A]│◄──────────►│ [Component B]│      │
│  │ ([metrics])  │            │ ([metrics])  │      │
│  └──────────────┘            └──────────────┘      │
└────────────────────────────────────────────────────┘

PROBLEMS:
❌ [Problem 1: Description]
❌ [Problem 2: Description]
❌ [Problem 3: Description]
```

#### After: [New State Description]

```
┌────────────────────────────────────────────────────┐
│                  [Component Name]                   │
│                   ([metrics])                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ FOCUSED RESPONSIBILITIES:                    │  │
│  │ • [Responsibility 1]                         │  │
│  │ • [Responsibility 2]                         │  │
│  └──────────────────────────────────────────────┘  │
│          │          │          │                    │
│          ▼          ▼          ▼                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │[Module A]│ │[Module B]│ │[Module C]│           │
│  │([metric])│ │([metric])│ │([metric])│           │
│  └──────────┘ └──────────┘ └──────────┘           │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │          [Abstraction Layer]                 │  │
│  │  • [Interface 1]                             │  │
│  │  • [Interface 2]                             │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘

BENEFITS:
✅ [Benefit 1: Description]
✅ [Benefit 2: Description]
✅ [Benefit 3: Description]
```

### Directory Tree: Complete Structure

```
[Detailed directory tree showing entire structure]
project_root/
├── file1.ext                    ([size])   [status/description]
├── file2.ext                    ([size])   [status/description]
│
├── folder1/                     [description]
│   ├── __init__.py              ([size])   [status]
│   ├── module1.ext              ([size])   [status/notes]
│   │
│   ├── subfolder/                ✨ NEW FOLDER
│   │   ├── __init__.py          ([size])   [status]
│   │   ├── new_module1.ext      ([size])   ✨ NEW - [purpose]
│   │   └── new_module2.ext      ([size])   ✨ NEW - [purpose]
│   │
│   └── file.ext                 ([size])   ✅
│
└── folder2/                     [description]
    ├── component1.ext           ([size])   ✅ Refactored
    ├── component2.ext           ([size])   ✅ Renamed
    └── component3.ext           ([size])   ✅
```

### Key Improvements Summary

#### 1. [Improvement Category 1]
- **Before**: [Metric/state]
- **After**: [Metric/state]
- **Impact**: [Description]

#### 2. [Improvement Category 2]
- **Before**: [Description]
- **After**: [Description]
- **Specific improvements**:
  - [Detail 1]
  - [Detail 2]

#### 3. [Additional Categories]
- Continue pattern for all major improvements

### Migration Impact

#### Breaking Changes
1. ❌ [Breaking change 1]: Description
2. ❌ [Breaking change 2]: Description
3. ❌ [Breaking change N]: Description

#### Non-Breaking Changes
1. ✅ [Compatible change 1]: Description
2. ✅ [Compatible change 2]: Description
3. ✅ [Compatible change N]: Description

#### Rollout Strategy
- **Phase X**: [Impact description]
- **Phase Y**: [Impact description]
- **Phase Z**: [Impact description]

---

**Document Version:** X.Y
**Created:** YYYY-MM-DD
**Last Updated:** YYYY-MM-DD
**Status:** [Current status]
**Next Steps:** [Immediate next action]
