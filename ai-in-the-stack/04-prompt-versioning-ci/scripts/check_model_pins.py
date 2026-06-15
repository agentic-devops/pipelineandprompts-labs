#!/usr/bin/env python3
# Path: prompt-versioning-ci-openshift/scripts/check_model_pins.py
# Purpose: Enforce model policy by checking spec.model against approved list
# Article: https://pipelineandprompts.com/posts/prompt-versioning-ci-openshift/

import sys
from pathlib import Path
import yaml


def main():
    if len(sys.argv) != 3:
        print("Usage: check_model_pins.py <prompts_directory> <policy_file>", file=sys.stderr)
        sys.exit(1)

    prompts_dir = Path(sys.argv[1])
    policy_file = Path(sys.argv[2])

    if not prompts_dir.is_dir():
        print(f"Error: {prompts_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if not policy_file.is_file():
        print(f"Error: {policy_file} does not exist", file=sys.stderr)
        sys.exit(1)

    # Load policy
    with open(policy_file, 'r') as f:
        policy = yaml.safe_load(f)

    approved_models = policy.get('approved_models', [])

    if not approved_models:
        print("Error: No approved_models found in policy file", file=sys.stderr)
        sys.exit(1)

    # Check all prompt files
    yaml_files = list(prompts_dir.glob('*.yaml')) + list(prompts_dir.glob('*.yml'))

    if not yaml_files:
        print(f"No YAML files found in {prompts_dir}", file=sys.stderr)
        sys.exit(1)

    violations = []

    for yaml_file in sorted(yaml_files):
        with open(yaml_file, 'r') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"WARNING: {yaml_file.name} — YAML parse error: {e}", file=sys.stderr)
                continue

        if not isinstance(data, dict):
            continue

        spec = data.get('spec', {})
        model = spec.get('model')

        if model and model not in approved_models:
            violations.append((yaml_file.name, model))
            print(f"FAIL: {yaml_file.name} — model '{model}' not in approved list", file=sys.stderr)
        elif model:
            print(f"PASS: {yaml_file.name} — model '{model}' approved")

    if violations:
        print(f"\n{len(violations)} file(s) use unapproved models", file=sys.stderr)
        print(f"Approved models: {', '.join(approved_models)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll {len(yaml_files)} prompt manifest(s) use approved models")
        sys.exit(0)


if __name__ == '__main__':
    main()
