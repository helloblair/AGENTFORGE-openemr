# Eval Generation Skill

## Purpose
Automatically generate eval test cases in `eval/test_cases.yaml` whenever a
tool or chain is added or modified.

## Rules — Apply After Every Tool/Chain Change

### 1. New Tool Added
Append **4** test cases to `eval/test_cases.yaml`:

| # | category    | description                                          |
|---|-------------|------------------------------------------------------|
| 1 | happy_path  | Tool works correctly with valid, typical input       |
| 2 | happy_path  | Tool works correctly with a different valid input    |
| 3 | edge_case   | Empty results, bad input, or boundary condition      |
| 4 | multi_step  | Chains this tool with at least one other tool        |

### 2. New Chain Added
Append **3** test cases to `eval/test_cases.yaml`:

| # | category   | description                                           |
|---|------------|-------------------------------------------------------|
| 1 | multi_step | Full chain trigger with standard input                |
| 2 | multi_step | Chain variation (different input or branching path)   |
| 3 | edge_case  | Chain with missing or partial data                    |

### 3. Tool Modified
Append **1-2** test cases covering the new or changed behavior only.

### 4. ID Numbering
- IDs follow the format `XX-NN` where `XX` is the category prefix and `NN` is
  a zero-padded sequence number.
- Category prefixes: `HP` (happy_path), `EC` (edge_case), `AD` (adversarial),
  `MS` (multi_step).
- Before appending, read the existing YAML and find the highest `NN` for each
  prefix. Increment from there. **Never reuse IDs.**

### 5. Adversarial Cases
Do **not** generate per-tool adversarial cases. The existing 10 adversarial
cases cover agent-level safety globally.

### 6. Case Format
Every appended case MUST follow this exact YAML structure:

```yaml
- id: "XX-NN"
  category: happy_path | edge_case | adversarial | multi_step
  input: "Natural-language query a user would type"
  expected_tools:
    - tool_name_1
    - tool_name_2
  expected_output_contains:
    - "string the response must include"
  pass_criteria: "Description of what correct behavior looks like"
```

### When NOT to Generate Cases
- Typo or formatting-only changes to a tool
- Changes to eval files themselves
- Documentation-only updates
