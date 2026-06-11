#!/usr/bin/env python3
# Path: prompt-versioning-ci-openshift/scripts/validate_prompts.py
# Purpose: Validate prompt manifest schema (required fields check)
# Article: https://pipelineandprompts.com/posts/prompt-versioning-ci-openshift/

import sys
from pathlib import Path
import yaml


def validate_prompt_file(file_path):
    """Validate a single prompt manifest file for required fields."""
    with open(file_path, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return False, f"YAML parse error: {e}"

    required_fields = [
        ('metadata', 'name'),
        ('metadata', 'version'),
        ('metadata', 'description'),
        ('metadata', 'tags'),
        ('spec', 'model'),
        ('spec', 'temperature'),
        ('spec', 'max_tokens'),
        ('spec', 'system'),
        ('spec', 'user_template'),
    ]

    missing_fields = []

    for *path, field in required_fields:
        current = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                missing_fields.append('.'.join(path + [field]))
                break
            current = current[key]
        else:
            if field not in current or current[field] in (None, '', []):
                missing_fields.append('.'.join(path + [field]))

    if missing_fields:
        return False, f"Missing or empty fields: {', '.join(missing_fields)}"

    return True, "Valid"


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_prompts.py <prompts_directory>", file=sys.stderr)
        sys.exit(1)

    prompts_dir = Path(sys.argv[1])

    if not prompts_dir.is_dir():
        print(f"Error: {prompts_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    yaml_files = list(prompts_dir.glob('*.yaml')) + list(prompts_dir.glob('*.yml'))

    if not yaml_files:
        print(f"No YAML files found in {prompts_dir}", file=sys.stderr)
        sys.exit(1)

    failures = []

    for yaml_file in sorted(yaml_files):
        valid, message = validate_prompt_file(yaml_file)
        if not valid:
            failures.append((yaml_file.name, message))
            print(f"FAIL: {yaml_file.name} — {message}", file=sys.stderr)
        else:
            print(f"PASS: {yaml_file.name}")

    if failures:
        print(f"\n{len(failures)} file(s) failed validation", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll {len(yaml_files)} prompt manifest(s) valid")
        sys.exit(0)


if __name__ == '__main__':
    main()
