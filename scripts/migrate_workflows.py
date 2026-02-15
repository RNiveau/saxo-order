#!/usr/bin/env python3
"""
One-time migration script to migrate workflows from YAML to DynamoDB.

Usage:
    poetry run python scripts/migrate_workflows.py
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml  # noqa: E402

sys.path.append(str(Path(__file__).parent.parent))

from client.aws_client import DynamoDBClient  # noqa: E402


def load_workflows_from_yaml(
    yaml_path: str = "workflows.yml",
) -> List[Dict[str, Any]]:
    """
    Load workflows from YAML file.

    Args:
        yaml_path: Path to workflows.yml file

    Returns:
        List of workflow dictionaries
    """
    with open(yaml_path, "r") as f:
        workflows = yaml.safe_load(f)
    return workflows if workflows else []


def validate_workflows(workflows: List[Dict[str, Any]]) -> None:
    """
    Validate workflows before migration.

    Checks for duplicate names and unsupported indicator types.

    Args:
        workflows: List of workflow dictionaries

    Raises:
        ValueError: If validation fails
    """
    seen_names: Set[str] = set()
    supported_indicators = {"ma50", "combo", "bbb", "bbh", "polarite", "zone"}

    for idx, workflow in enumerate(workflows):
        name = workflow.get("name")
        if not name:
            raise ValueError(f"Workflow at index {idx} missing 'name' field")

        if name in seen_names:
            raise ValueError(f"Duplicate workflow name found: {name}")
        seen_names.add(name)

        for cond_idx, condition in enumerate(workflow.get("conditions", [])):
            indicator_name = condition.get("indicator", {}).get("name")
            if indicator_name not in supported_indicators:
                msg = (
                    f"Unsupported indicator type '{indicator_name}'"
                    f" in workflow '{name}' condition {cond_idx}"
                )
                raise ValueError(msg)


def convert_end_date(end_date: Any) -> Any:
    """
    Convert end_date from YYYY/MM/DD to ISO 8601 format (YYYY-MM-DD).

    Args:
        end_date: End date string in YYYY/MM/DD format or None

    Returns:
        ISO 8601 date string or None
    """
    if not end_date:
        return None
    if isinstance(end_date, str) and "/" in end_date:
        return end_date.replace("/", "-")
    return end_date


def apply_default_trigger(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default trigger configuration if missing.

    Defaults:
    - ut: h1
    - signal: breakout
    - location: "higher" if first condition direction is "above",
      else "lower"
    - order_direction: "buy" if first condition direction is
      "above", else "sell"
    - quantity: 0.1

    Args:
        workflow: Workflow dictionary

    Returns:
        Trigger dictionary with defaults applied
    """
    if "trigger" in workflow and workflow["trigger"]:
        return workflow["trigger"]

    first_condition = workflow.get("conditions", [{}])[0]
    close_direction = first_condition.get("close", {}).get(
        "direction", "above"
    )

    return {
        "ut": "h1",
        "signal": "breakout",
        "location": "higher" if close_direction == "above" else "lower",
        "order_direction": "buy" if close_direction == "above" else "sell",
        "quantity": 0.1,
    }


def transform_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform YAML workflow to DynamoDB format.

    Generates UUID, converts dates, applies defaults, adds timestamps.

    Args:
        workflow: Raw workflow from YAML

    Returns:
        Transformed workflow ready for DynamoDB
    """
    workflow_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    transformed = {
        "id": workflow_id,
        "name": workflow["name"],
        "index": workflow["index"],
        "cfd": workflow["cfd"],
        "enable": workflow.get("enable", True),
        "dry_run": workflow.get("dry_run", False),
        "is_us": workflow.get("is_us", False),
        "end_date": convert_end_date(workflow.get("end_date")),
        "conditions": workflow.get("conditions", []),
        "trigger": apply_default_trigger(workflow),
        "created_at": now,
        "updated_at": now,
    }

    return transformed


def migrate_workflows(
    yaml_path: str = "workflows.yml", dry_run: bool = False
) -> List[str]:
    """
    Main migration function.

    Args:
        yaml_path: Path to workflows.yml file
        dry_run: If True, only validate without inserting to DynamoDB

    Returns:
        List of created workflow IDs for rollback capability
    """
    print(f"Loading workflows from {yaml_path}...")
    workflows = load_workflows_from_yaml(yaml_path)
    print(f"Found {len(workflows)} workflows to migrate")

    print("Validating workflows...")
    validate_workflows(workflows)
    print(f"Validation complete: {len(workflows)} valid workflows")

    if dry_run:
        print("DRY RUN: Skipping DynamoDB insertion")
        return []

    print("Transforming workflows...")
    transformed_workflows = [transform_workflow(w) for w in workflows]

    print("Migrating workflows to DynamoDB...")
    dynamodb_client = DynamoDBClient()
    created_ids = []

    try:
        for idx, workflow in enumerate(transformed_workflows, 1):
            created_ids.append(workflow["id"])
            total = len(transformed_workflows)
            print(f"[{idx}/{total}] Migrating: {workflow['name']}")

        dynamodb_client.batch_put_workflows(transformed_workflows)

        count = len(transformed_workflows)
        print(f"\nMigration complete: {count} workflows created")
        return created_ids

    except Exception as e:
        print(f"\nERROR during migration: {e}")
        print(f"Created {len(created_ids)} workflows before failure")
        print(
            "Rollback capability:" " IDs tracked for manual cleanup if needed"
        )
        raise


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate workflows from YAML to DynamoDB"
    )
    parser.add_argument(
        "--yaml",
        default="workflows.yml",
        help="Path to workflows.yml file (default: workflows.yml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, do not insert to DynamoDB",
    )

    args = parser.parse_args()

    try:
        created_ids = migrate_workflows(
            yaml_path=args.yaml, dry_run=args.dry_run
        )
        if not args.dry_run:
            print("\nCreated workflow IDs (for reference):")
            for wf_id in created_ids[:5]:
                print(f"  - {wf_id}")
            if len(created_ids) > 5:
                print(f"  ... and {len(created_ids) - 5} more")
        sys.exit(0)
    except Exception as e:
        print(f"\nMigration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
