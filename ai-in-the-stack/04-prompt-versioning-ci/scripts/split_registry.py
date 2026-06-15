#!/usr/bin/env python3
# Path: prompt-versioning-ci-openshift/scripts/split_registry.py
# Purpose: Split prompts into domain-specific ConfigMaps (by first tag)
# Article: https://pipelineandprompts.com/posts/prompt-versioning-ci-openshift/
#
# Usage: ./split_registry.py > manifests/prompt-configmaps.yaml
#        kubectl apply -f manifests/prompt-configmaps.yaml

import sys
from pathlib import Path
import yaml


def main():
    prompts_dir = Path('prompts')

    if not prompts_dir.is_dir():
        print("Error: prompts/ directory not found", file=sys.stderr)
        sys.exit(1)

    yaml_files = list(prompts_dir.glob('*.yaml')) + list(prompts_dir.glob('*.yml'))

    if not yaml_files:
        print("Error: No YAML files found in prompts/", file=sys.stderr)
        sys.exit(1)

    # Group prompts by first tag (domain)
    domain_groups = {}

    for yaml_file in sorted(yaml_files):
        with open(yaml_file, 'r') as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"WARNING: Skipping {yaml_file.name} — YAML parse error: {e}", file=sys.stderr)
                continue

        if not isinstance(data, dict):
            continue

        metadata = data.get('metadata', {})
        tags = metadata.get('tags', [])

        if not tags:
            domain = 'general'
        else:
            domain = tags[0]

        if domain not in domain_groups:
            domain_groups[domain] = []

        domain_groups[domain].append({
            'filename': yaml_file.name,
            'content': yaml.dump(data, default_flow_style=False, sort_keys=False)
        })

    # Generate ConfigMap manifests
    configmaps = []

    for domain, prompts in sorted(domain_groups.items()):
        data_dict = {}
        for prompt in prompts:
            data_dict[prompt['filename']] = prompt['content']

        configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': f'prompt-registry-{domain}',
                'namespace': 'ai-workflows',
                'labels': {
                    'app': 'prompt-registry',
                    'domain': domain
                }
            },
            'data': data_dict
        }

        configmaps.append(configmap)

    # Output all ConfigMaps separated by ---
    for i, cm in enumerate(configmaps):
        if i > 0:
            print('---')
        print(yaml.dump(cm, default_flow_style=False, sort_keys=False))

    print(f"# Generated {len(configmaps)} ConfigMap(s) from {len(yaml_files)} prompt(s)", file=sys.stderr)


if __name__ == '__main__':
    main()
