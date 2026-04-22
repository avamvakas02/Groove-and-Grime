# Generated manually to safely repair DB schema drift without data loss.
from django.db import migrations


def _column_names(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )
    return {col.name for col in description}


def reconcile_schema(apps, schema_editor):
    vinyl_table = "catalogue_vinylrecord"
    category_table = "catalogue_category"

    vinyl_cols = _column_names(schema_editor, vinyl_table)
    category_cols = _column_names(schema_editor, category_table)

    q_vinyl = schema_editor.quote_name(vinyl_table)
    q_category = schema_editor.quote_name(category_table)

    if "stock" not in vinyl_cols:
        schema_editor.execute(
            f"ALTER TABLE {q_vinyl} ADD COLUMN stock integer NOT NULL DEFAULT 1"
        )
    if "is_exclusive" not in vinyl_cols:
        schema_editor.execute(
            f"ALTER TABLE {q_vinyl} ADD COLUMN is_exclusive bool NOT NULL DEFAULT 0"
        )
    if "created_at" not in vinyl_cols:
        schema_editor.execute(f"ALTER TABLE {q_vinyl} ADD COLUMN created_at datetime")
        schema_editor.execute(
            f"UPDATE {q_vinyl} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )

    if "description" not in category_cols:
        schema_editor.execute(f"ALTER TABLE {q_category} ADD COLUMN description text")


class Migration(migrations.Migration):
    dependencies = [
        ("catalogue", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(reconcile_schema, migrations.RunPython.noop),
    ]
