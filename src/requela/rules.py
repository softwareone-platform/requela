from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from requela.builders import QueryBuilder, get_builder_for_model
from requela.dataclasses import Operator
from requela.exceptions import RequelaError

DOCS_HEADER = [
    "| Field | Operators | Order By |",
    "|-------|-----------|----------|",
]


@dataclass
class FieldRule:
    allowed_operators: set[Operator] | None = None
    alias: str | None = None
    allow_ordering: bool = True
    source: str | None = None
    # Converts a value, already cast to the field's type, to the stored format
    value_converter: Callable[[Any], Any] | None = None


@dataclass
class RelationshipRule:
    rules: ModelRQLRules
    alias: str | None = None


class ModelRQLRules:
    __model__: ClassVar[Any]
    # Builder class to use; when not set, it is inferred from the model (SQLAlchemy, Django)
    __builder__: ClassVar[type[QueryBuilder] | None] = None
    _fields: ClassVar[dict[str, FieldRule]]
    _relations: ClassVar[dict[str, RelationshipRule]]

    def __init_subclass__(cls):
        super().__init_subclass__()

        # Abstract rules classes only share settings (e.g. `__builder__`) with subclasses.
        # Read from the class itself so that subclasses of an abstract class are concrete.
        if cls.__dict__.get("__abstract__", False):
            return

        if not hasattr(cls, "__model__"):
            raise TypeError(f"{cls.__name__} must define __model__")

        fields = {}
        relations = {}

        for attr_name in dir(cls):
            attr_value = getattr(cls, attr_name)

            if isinstance(attr_value, FieldRule):
                fields[attr_name] = attr_value
            elif isinstance(attr_value, RelationshipRule):
                relations[attr_name] = attr_value

        cls._fields = fields
        cls._relations = relations

    def __init__(self):
        if self.__class__.__dict__.get("__abstract__", False):
            raise TypeError(f"{self.__class__.__name__} is abstract and cannot be instantiated")
        self.builder = self._get_builder()
        self._validate()

    def build_query(self, rql_expression: str, initial_query: Any = None) -> Any:
        """Builds the query using the configured builder"""
        try:
            return self.builder.build_query(
                rql_expression,
                initial_query=initial_query,
            )
        except (ValueError, TypeError, AttributeError) as e:
            raise RequelaError(str(e)) from e

    def get_documentation(self) -> str:
        """Returns the documentation for the rules"""
        docs = DOCS_HEADER + self._get_fields_documentation()
        return "\n".join(docs)

    def _get_fields_documentation(self, alias_prefix: str = "") -> list[str]:
        """Returns the documentation for the rules"""

        docs = []
        for field_name, field in self._fields.items():
            operators = ", ".join(sorted([op.value for op in field.allowed_operators]))  # type: ignore
            prefix = ""
            if alias_prefix:
                prefix = f"{alias_prefix}."
            docs.append(
                f"|{prefix}{field.alias or field_name}"
                f"|{operators}|{'yes' if field.allow_ordering else 'no'}|"
            )
        for relation_name, relation in self._relations.items():
            prefix = ""
            if alias_prefix:
                prefix = f"{alias_prefix}."
            docs.append(f"|{prefix}{relation.alias or relation_name}|eq, ne|no|")
            docs.extend(
                relation.rules._get_fields_documentation(
                    f"{prefix}{relation.alias or relation_name}"
                )
            )
        return sorted(docs)

    @classmethod
    def _resolve_alias(cls, alias: str) -> str:
        field_name, field_def = cls._get_field_by_alias(alias)
        if isinstance(field_def, FieldRule) and field_def.source:
            return field_def.source
        return field_name

    @classmethod
    def _validate_operator_and_field(cls, field: str, operator: Operator):
        _, field_def = cls._get_field_by_alias(field)
        allowed_operators = (
            field_def.allowed_operators
            if isinstance(field_def, FieldRule)
            else {Operator.EQ, Operator.NE}
        )
        if operator not in allowed_operators:  # type: ignore
            raise ValueError(f"Operator '{operator.value}' is not allowed for field '{field}'.")

    @classmethod
    def _validate_ordering(cls, field: str):
        _, field_def = cls._get_field_by_alias(field)
        if not field_def.allow_ordering:  # type: ignore
            raise ValueError(f"Order by '{field}' is not allowed.")

    @classmethod
    def _get_field_rule(cls, alias: str) -> FieldRule | RelationshipRule:
        _, field_def = cls._get_field_by_alias(alias)
        return field_def

    @classmethod
    def _get_builder(cls) -> QueryBuilder:
        callbacks = {
            "resolve_alias_callback": cls._resolve_alias,
            "validate_operator_and_field_callback": cls._validate_operator_and_field,
            "validate_ordering_callback": cls._validate_ordering,
            "get_field_rule_callback": cls._get_field_rule,
        }
        if cls.__builder__ is not None:
            return cls.__builder__(cls.__model__, **callbacks)
        return get_builder_for_model(cls.__model__, **callbacks)

    def _validate(self) -> None:
        errors = []

        for field_name, field_def in self._fields.items():
            try:
                # Get field type from model (implementation depends on ORM)
                lookup = field_def.source or field_name
                field_type = self._get_field_type(lookup)

                # If no operators specified, infer from field type
                if field_def.allowed_operators is None:
                    default_operators = self.builder.get_default_operators(field_type)

                    if default_operators is None:  # pragma: no cover
                        errors.append(
                            f"Cannot infer default operators for field {field_name} "
                            f"of type {field_type}"
                        )
                    else:
                        field_def.allowed_operators = default_operators

                # Validate that the operators are compatible with the field type
                if field_def.allowed_operators:  # pragma: no branch
                    invalid_ops = self._validate_operators(field_type, field_def.allowed_operators)
                    if invalid_ops:
                        invalid_ops_str = ", ".join(sorted([f"'{op.value}'" for op in invalid_ops]))
                        errors.append(
                            f"Invalid operators {invalid_ops_str} for field '{field_name}' "
                            f"of type '{field_type.__name__}'."
                        )

            except AttributeError:
                errors.append(
                    f"Field '{field_name}' not found in model '{self.__model__.__name__}'."
                )
            except TypeError as e:
                errors.append(str(e))

        if errors:
            raise ExceptionGroup(
                f"Model validation failed for '{self.__model__.__name__}'",
                [ValueError(error_msg) for error_msg in errors],
            )

    def _get_field_type(self, field_name: str) -> type:
        """Gets the type of a field - to be implemented by specific ORM builders"""
        return self.builder.get_field_type(field_name)

    def _validate_operators(self, field_type: type, operators: set[Operator]) -> set[Operator]:
        """Validates operators against field type"""

        valid_operators = self.builder.get_default_operators(field_type)

        if not valid_operators:  # pragma: no cover
            return operators

        return {op for op in operators if op not in valid_operators}  # type: ignore

    @classmethod
    def _get_relation_by_alias(cls, alias: str) -> tuple[str, RelationshipRule]:
        relations = {}
        for relation_name, relation_def in cls._relations.items():
            relation_field_name = relation_def.alias or relation_name
            if alias == relation_field_name or alias.startswith(f"{relation_field_name}."):
                relations[relation_name] = relation_def
        if not relations:
            raise ValueError(f"Relation with alias '{alias}' not found")
        if len(relations) > 1:
            raise ValueError(f"Multiple relations found for alias '{alias}'")
        return next(iter(relations.items()))

    @classmethod
    def _get_field_by_alias(cls, alias: str) -> tuple[str, FieldRule | RelationshipRule]:
        """Gets a field definition by its alias or field name"""
        # First, check local fields
        for field_name, field_def in cls._fields.items():
            if field_def.alias == alias or field_name == alias:
                return field_name, field_def

        relation_name, relation_def = cls._get_relation_by_alias(alias)
        relation_field_name = relation_def.alias or relation_name
        if alias == relation_field_name:
            return relation_name, relation_def
        field_to_search = alias.removeprefix(relation_field_name)[1:] or relation_field_name
        f_name, f_def = relation_def.rules._get_field_by_alias(field_to_search)
        return f"{relation_name}.{f_name}", f_def
