from django.db import migrations


def reconcile_review_schema(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'sqlite':
        # This reconciliation migration targets legacy SQLite-only schema drift.
        # Postgres/MySQL deployments already get the correct Review schema via 0004.
        return

    table_name = 'catalogue_review'

    with connection.cursor() as cursor:
        # Table may not exist in some environments; skip safely.
        existing_tables = connection.introspection.table_names(cursor)
        if table_name not in existing_tables:
            return

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}

        if 'created_at' not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN created_at datetime")
            cursor.execute(f"UPDATE {table_name} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

        if 'updated_at' not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN updated_at datetime")
            cursor.execute(f"UPDATE {table_name} SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

        # Ensure one review per user/record pair even on legacy tables.
        cursor.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {table_name}_user_record_uniq_idx "
            f"ON {table_name}(user_id, record_id)"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('catalogue', '0004_review'),
    ]

    operations = [
        migrations.RunPython(reconcile_review_schema, migrations.RunPython.noop),
    ]
