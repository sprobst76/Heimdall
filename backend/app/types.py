"""Portable SQL types that work across PostgreSQL and SQLite.

PostgreSQL uses native UUID, ARRAY, and JSON types.
SQLite uses CHAR(32), JSON, and JSON respectively.
"""

import uuid as _uuid

import sqlalchemy as sa
from sqlalchemy import JSON, TypeDecorator


class UUIDArray(TypeDecorator):
    """PostgreSQL ``ARRAY(UUID)`` on PG, JSON list on other dialects."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY, UUID

            return dialect.type_descriptor(ARRAY(UUID(as_uuid=True)))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is not None and dialect.name != "postgresql":
            return [str(v) for v in value]
        return value

    def process_result_value(self, value, dialect):
        if value is not None and dialect.name != "postgresql":
            return [_uuid.UUID(v) for v in value]
        return value


class TextArray(TypeDecorator):
    """PostgreSQL ``ARRAY(Text)`` on PG, JSON list on other dialects."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY

            return dialect.type_descriptor(ARRAY(sa.Text()))
        return dialect.type_descriptor(JSON())
