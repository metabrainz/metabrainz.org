from unittest import TestCase
from unittest.mock import Mock, patch

from metabrainz.user import migrate_mb_users


class OldEditorNameMigrationTestCase(TestCase):

    def test_insert_old_username_batch(self):
        cursor = Mock()
        cursor.rowcount = 2
        rows = [{"name": "former-editor"}, {"name": "another-former-editor"}]

        with patch.object(migrate_mb_users, "execute_values") as execute_values:
            written = migrate_mb_users._insert_old_username_batch(cursor, rows)

        self.assertEqual(written, 2)
        execute_values.assert_called_once_with(
            cursor,
            migrate_mb_users.INSERT_OLD_USERNAMES_QUERY,
            rows,
            template=migrate_mb_users.INSERT_OLD_USERNAME_TEMPLATE,
            page_size=2,
        )

    def test_insert_old_username_batch_skips_empty_batch(self):
        with patch.object(migrate_mb_users, "execute_values") as execute_values:
            written = migrate_mb_users._insert_old_username_batch(Mock(), [])

        self.assertEqual(written, 0)
        execute_values.assert_not_called()

    def test_migrate_old_editor_names_reads_in_batches(self):
        mb_cursor = Mock()
        meb_cursor = Mock()
        mb_cursor.fetchmany.side_effect = [
            [{"name": "first"}, {"name": "second"}],
            [{"name": "already-present"}],
            [],
        ]

        with patch.object(
            migrate_mb_users,
            "_insert_old_username_batch",
            side_effect=[2, 0],
        ) as insert_batch:
            result = migrate_mb_users._migrate_old_editor_names(
                mb_cursor, meb_cursor, batch_size=2
            )

        self.assertEqual(result, (2, 1))
        mb_cursor.execute.assert_called_once_with(
            migrate_mb_users.FETCH_OLD_EDITOR_NAMES_QUERY
        )
        self.assertEqual(mb_cursor.fetchmany.call_count, 3)
        insert_batch.assert_any_call(
            meb_cursor, [{"name": "first"}, {"name": "second"}]
        )
        insert_batch.assert_any_call(meb_cursor, [{"name": "already-present"}])
