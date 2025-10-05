"""
DynamoDB Schema Migration Script

Migrates existing workflows to support multi-agent schema v2.0
Adds agent_states field and schema_version while maintaining backward compatibility.
"""

import boto3
from datetime import datetime, timezone
import json


def migrate_dynamodb_schema():
    """
    Migrate DynamoDB table to support multi-agent architecture

    Changes:
    - Add agent_states field (if missing)
    - Add schema_version field (if missing)
    - Maintain backward compatibility with existing workflows
    """
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('blog-workflow-state')

    print("Starting DynamoDB schema migration...")
    print("=" * 60)

    try:
        # Scan all items
        response = table.scan()
        items = response.get('Items', [])

        print(f"Found {len(items)} workflows to migrate")

        migrated_count = 0
        skipped_count = 0

        for item in items:
            workflow_id = item.get('workflow_id')

            # Check if already migrated
            if 'schema_version' in item and item['schema_version'] == '2.0':
                print(f"✓ Skipping {workflow_id} - already migrated")
                skipped_count += 1
                continue

            # Prepare updates
            update_expression_parts = []
            expression_attribute_values = {}

            # Add agent_states if missing
            if 'agent_states' not in item:
                update_expression_parts.append("agent_states = :empty_dict")
                expression_attribute_values[':empty_dict'] = {}

            # Add schema_version
            update_expression_parts.append("schema_version = :version")
            expression_attribute_values[':version'] = "2.0"

            # Add updated_at
            update_expression_parts.append("updated_at = :updated_at")
            expression_attribute_values[':updated_at'] = datetime.now(timezone.utc).isoformat()

            # Execute update
            if update_expression_parts:
                update_expression = "SET " + ", ".join(update_expression_parts)

                table.update_item(
                    Key={'workflow_id': workflow_id},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values
                )

                print(f"✓ Migrated {workflow_id}")
                migrated_count += 1

        print("=" * 60)
        print(f"Migration complete!")
        print(f"  - Migrated: {migrated_count}")
        print(f"  - Skipped: {skipped_count}")
        print(f"  - Total: {len(items)}")

        # Verify migration
        print("\nVerifying migration...")
        response = table.scan(
            FilterExpression="attribute_not_exists(schema_version) OR schema_version <> :version",
            ExpressionAttributeValues={':version': '2.0'}
        )

        unmigrated = response.get('Items', [])
        if unmigrated:
            print(f"⚠ WARNING: {len(unmigrated)} workflows not migrated:")
            for item in unmigrated:
                print(f"  - {item.get('workflow_id')}")
        else:
            print("✓ All workflows successfully migrated to schema v2.0")

    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    print("\nDynamoDB Schema Migration for Multi-Agent Blog Automation")
    print("This will add agent_states and schema_version to all workflows")
    print("=" * 60)

    response = input("\nProceed with migration? (yes/no): ")

    if response.lower() == 'yes':
        migrate_dynamodb_schema()
    else:
        print("Migration cancelled.")
