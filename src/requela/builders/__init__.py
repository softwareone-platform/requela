from collections.abc import Callable
from typing import Any

from requela.builders.base import QueryBuilder


def get_builder_for_model(
    model: Any,
    resolve_alias_callback: Callable | None = None,
    validate_operator_and_field_callback: Callable | None = None,
    validate_ordering_callback: Callable | None = None,
):
    """Returns appropriate builder based on model type"""

    # SQLAlchemy model
    if hasattr(model, "__table__"):
        from requela.builders.sqlalchemy import SQLAlchemyQueryBuilder

        return SQLAlchemyQueryBuilder(
            model,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
            validate_ordering_callback=validate_ordering_callback,
        )
    # Django model
    elif hasattr(model, "_meta"):  # pragma: no branch
        from requela.builders.django import DjangoQueryBuilder

        return DjangoQueryBuilder(
            model,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
            validate_ordering_callback=validate_ordering_callback,
        )
    else:  # pragma: no cover
        raise ValueError(f"Unsupported model type: {type(model)}")


__all__ = ["get_builder_for_model", "QueryBuilder"]
