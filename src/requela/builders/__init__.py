from collections.abc import Callable
from typing import Any

from requela.builders.base import QueryBuilder


def get_builder_for_model(
    model: Any,
    resolve_alias_callback: Callable | None = None,
    validate_operator_and_field_callback: Callable | None = None,
):
    """Returns appropriate builder based on model type"""

    if hasattr(model, "__table__"):  # SQLAlchemy model
        from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder

        return SQLAlchemyQueryBuilder(
            model,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
        )
    elif hasattr(model, "_meta"):  # Django model
        from requela.builders.django import DjangoQueryBuilder

        return DjangoQueryBuilder(
            model,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
        )
    else:
        raise ValueError(f"Unsupported model type: {type(model)}")


__all__ = ["get_builder_for_model", "QueryBuilder"]
