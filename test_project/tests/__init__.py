import io
import os
import unittest

from django.core.management import call_command
from django.test import TestCase, modify_settings

settings_module = os.environ["DJANGO_SETTINGS_MODULE"]


class MigrateMixin:
    def test_migrate(self):
        try:
            call_command("migrate")
        except Exception:
            self.assertTrue(False, "Migrations failed")
        else:
            self.assertTrue(True, "Migrations succeded")


class CommandOutputMixin:
    def get_command_output(self, cmd, *cmd_args, **cmd_options):
        file_obj = io.StringIO()
        cmd_options.update(stdout=file_obj)
        call_command(cmd, *cmd_args, **cmd_options)
        output = file_obj.getvalue()

        file_obj.close()
        return output


class MigrationsTesterBase(MigrateMixin, CommandOutputMixin):
    bool_match = "ALTER COLUMN \"is_functional\" SET DEFAULT 'False';"
    text_match = (
        'ALTER TABLE "dadv_testtextdefault" ALTER COLUMN "description" '
        "SET DEFAULT 'No description provided';"
    )
    charfield_match = (
        'ALTER TABLE "dadv_testhappypath" ALTER COLUMN "name" '
        "SET DEFAULT 'Happy path'"
    )
    date_match = 'ALTER TABLE "dadv_testhappypath" ALTER COLUMN "dob" SET DEFAULT \'1970-01-01\';'
    current_timestamp_match = (
        'ALTER TABLE "dadv_testhappypath" ALTER COLUMN "rebirth" SET DEFAULT now();'
    )
    current_date_match = (
        'ALTER TABLE "dadv_testhappypath" ALTER COLUMN "married" SET DEFAULT now();'
    )

    def test_bool_default(self):
        actual = self.get_command_output("sqlmigrate", "dadv", "0001")
        self.assertIn(self.bool_match, actual)

    def test_text_default(self):
        """Make sure we can add defaults for text fields"""
        actual = self.get_command_output("sqlmigrate", "dadv", "0002")
        self.assertIn(self.text_match, actual)

    def test_charfield_default(self):
        """Make sure we can add defaults for char fields"""
        actual = self.get_command_output("sqlmigrate", "dadv", "0003")
        self.assertIn(self.charfield_match, actual)

    def test_default_date(self):
        """Make sure temporal values work"""
        actual = self.get_command_output("sqlmigrate", "dadv", "0004")
        self.assertIn(self.date_match, actual)

    def test_current_timestamp(self):
        """Make sure we can provide current timestamps as default"""
        actual = self.get_command_output("sqlmigrate", "dadv", "0004")
        self.assertIn(self.current_timestamp_match, actual)

    def test_current_date(self):
        """Make sure we can provide current dates as default"""
        actual = self.get_command_output("sqlmigrate", "dadv", "0004")
        self.assertIn(self.current_date_match, actual)


@modify_settings(INSTALLED_APPS={"append": "dadv.apps.DadvConfig"})
class MigrationsTesterPgSQL(TestCase, MigrationsTesterBase):
    pass
