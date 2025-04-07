# Copyright 2020 Mariana Tek
# Copyright 2018 3YOURMIND GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
from datetime import date, datetime

import django
from django.db.migrations.operations.base import Operation
from django.db import models

NOW = "__NOW__"
TODAY = "__TODAY__"
START = 0
END = 1


def is_text_field(model, field_name):
    options = model._meta  # type: models.base.Options
    field = options.get_field(field_name)
    return isinstance(field, models.TextField)


def is_date_field(model, field_name):
    options = model._meta  # type: models.base.Options
    field = options.get_field(field_name)
    return isinstance(field, models.DateField)


class AddDefaultValue(Operation):
    reversible = True
    quotes = {
        "value": ("'", "'"),
        "constant": ("", ""),
        "function": ("", ""),
        "name": ('"', '"'),
    }

    def __init__(self, model_name, name, value):
        self.model_name = model_name
        self.name = name
        self.value = value

    def describe(self):
        """
        Output a brief summary of what the action does.
        """
        return "Add to field {model}.{field} the default value {value}".format(
            model=self.model_name, field=self.name, value=self.value
        )

    def state_forwards(self, app_label, state):
        """
        Take the state from the previous migration, and mutate it
        so that it matches what this migration would perform.
        """
        # Nothing to do
        # because the field should have the default set anyway
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        """
        Perform the mutation on the database schema in the normal
        (forwards) direction.
        """
        if not self.is_supported_vendor(schema_editor.connection.vendor):
            return

        to_model = to_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, to_model):
            return

        self.initialize_vendor_state(schema_editor)

        to_model = to_state.apps.get_model(app_label, self.model_name)

        sql_value, value_quote = self.clean_value(
            schema_editor.connection.vendor, self.value
        )
        format_kwargs = dict(
            table=to_model._meta.db_table,
            field=self.name,
            value=sql_value,
            value_quote_start=value_quote[START],
            value_quote_end=value_quote[END],
            name_quote_start=self.quotes["name"][START],
            name_quote_end=self.quotes["name"][END],
        )
        sql_query = (
            "ALTER TABLE {name_quote_start}{table}{name_quote_end} "
            "ALTER COLUMN {name_quote_start}{field}{name_quote_end} "
            "SET DEFAULT {value_quote_start}{value}{value_quote_end};".format(
                **format_kwargs
            )
        )

        schema_editor.execute(sql_query)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        """
        Perform the mutation on the database schema in the reverse
        direction - e.g. if this were CreateModel, it would in fact
        drop the model's table.
        """
        if not self.is_supported_vendor(schema_editor.connection.vendor):
            return

        to_model = to_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, to_model):
            return

        self.initialize_vendor_state(schema_editor)

        to_model = to_state.apps.get_model(app_label, self.model_name)

        format_kwargs = dict(
            table=to_model._meta.db_table,
            field=self.name,
            name_quote_start=self.quotes["name"][START],
            name_quote_end=self.quotes["name"][END],
        )
        sql_query = (
            "ALTER TABLE {name_quote_start}{table}{name_quote_end} "
            "ALTER COLUMN {name_quote_start}{field}{name_quote_end} "
            "DROP DEFAULT;".format(**format_kwargs)
        )

        schema_editor.execute(sql_query)

    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {"model_name": self.model_name, "name": self.name, "value": self.value},
        )

    def initialize_vendor_state(self, schema_editor):
        self.quotes["name"] = ('"', '"')
        major, minor, patch, __, ___ = django.VERSION

    @classmethod
    def is_supported_vendor(cls, vendor):
        return vendor.startswith("postgre")

    def clean_value(self, vendor, value):
        """
        Lie, cheat and apply plastic surgery where needed

        :param vendor: database vendor we need to perform operations for
        :param value: the value as provided in the migration
        :return: a 2-tuple containing the new value and the quotation to use
        """

        value, quote, handled = self._clean_temporal(vendor, value)
        if handled:
            return value, quote

        value, quote, handled = self._clean_temporal_constants(vendor, value)
        if handled:
            return value, quote

        return value, self.quotes["value"]

    def _clean_temporal(self, vendor, value):
        if isinstance(value, date):
            return value.isoformat(), self.quotes["value"], True

        if isinstance(value, datetime):
            return (
                value.isoformat(" ", timespec="seconds"),
                self.quotes["value"],
                True,
            )

        return value, self.quotes["value"], False

    def _clean_temporal_constants(self, vendor, value):
        if value == NOW or value == TODAY:
            return "now()", self.quotes["function"], True

        return value, self.quotes["value"], False
