#!/usr/bin/env python3
"""Fix duplicate workflow names by appending zone values."""

from collections import defaultdict

import yaml

# Load workflows
with open("workflows.yml", "r") as f:
    workflows = yaml.safe_load(f)

# Group by name
name_groups = defaultdict(list)
for i, wf in enumerate(workflows):
    name_groups[wf["name"]].append((i, wf))

# Fix duplicates
for name, group in name_groups.items():
    if len(group) > 1:
        print(f"Fixing {len(group)} duplicates for: {name}")
        for idx, (i, wf) in enumerate(group):
            # Get zone values
            try:
                indicator = wf["conditions"][0]["indicator"]
                value = indicator.get("value", "")
                zone_value = indicator.get("zone_value", "")
                new_name = f"{name} {value}-{zone_value}"
                workflows[i]["name"] = new_name
                print(f"  -> {new_name}")
            except (KeyError, IndexError, TypeError):
                # If can't get zone values, just append index
                new_name = f"{name} {idx + 1}"
                workflows[i]["name"] = new_name
                print(f"  -> {new_name} (fallback)")

# Save
with open("workflows.yml", "w") as f:
    yaml.dump(
        workflows,
        f,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

print("\n✅ Fixed all duplicate workflow names!")
