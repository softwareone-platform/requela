from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum
from typing import Any, ClassVar

from requela.builders import QueryBuilder, get_builder_for_model
from requela.dataclasses import DEFAULT_OPERATORS, Operator


@dataclass
class FieldRule:
    allowed_operators: set[Operator] | None = None
    alias: str | None = None
    allow_ordering: bool = True


@dataclass
class RelationshipRule:
    alias: str
    rules: ModelRQLRules


class ModelRQLRulesMeta(type):
    def __new__(mcs, name, bases, namespace):
        if name == "ModelRQLRules":
            return super().__new__(mcs, name, bases, namespace)

        if "__model__" not in namespace:
            raise ValueError(f"{name} must define __model__")

        fields = {}
        relations = {}

        # Collect fields and relations from the current class
        for key, value in namespace.items():
            if isinstance(value, FieldRule):
                fields[key] = value
            elif isinstance(value, RelationshipRule):
                relations[key] = value

        # Collect fields and relations from base classes
        for base in bases:
            for key, value in vars(base).items():
                if isinstance(value, FieldRule) and key not in fields:
                    fields[key] = value
                elif isinstance(value, RelationshipRule) and key not in relations:
                    relations[key] = value

        def collect_rules_from_bases(cls):
            for key, value in vars(cls).items():
                if isinstance(value, FieldRule) and key not in fields:
                    fields[key] = value
                elif isinstance(value, RelationshipRule) and key not in relations:
                    relations[key] = value

            for base in cls.__bases__:
                collect_rules_from_bases(base)

        # Start collecting from the direct bases
        for base in bases:
            collect_rules_from_bases(base)

        namespace["_fields"] = fields
        namespace["_relations"] = relations
        return super().__new__(mcs, name, bases, namespace)


class ModelRQLRules(metaclass=ModelRQLRulesMeta):
    __model__: ClassVar[Any]
    _fields: ClassVar[dict[str, FieldRule]]
    _relations: ClassVar[dict[str, RelationshipRule]]

    def __init__(self):
        self.builder = self._get_builder()
        self._validate()

    def build_query(self, rql_expression: str, initial_query: Any = None) -> Any:
        """Builds the query using the configured builder"""
        return self.builder.build_query(
            rql_expression,
            initial_query=initial_query,
        )

    @classmethod
    def _resolve_alias(cls, alias: str) -> str:
        field_name, _ = cls._get_field_by_alias(alias)
        return field_name

    @classmethod
    def _validate_operator_and_field(cls, field: str, operator: Operator):
        _, field_def = cls._get_field_by_alias(field)
        if operator not in field_def.allowed_operators:  # type: ignore
            raise ValueError(f"Operator '{operator.value}' is not allowed for field '{field}'.")

    @classmethod
    def _validate_ordering(cls, field: str):
        _, field_def = cls._get_field_by_alias(field)
        if not field_def.allow_ordering:  # type: ignore
            raise ValueError(f"Order by '{field}' is not allowed.")

    @classmethod
    def _get_builder(cls) -> QueryBuilder:
        return get_builder_for_model(
            cls.__model__,
            resolve_alias_callback=cls._resolve_alias,
            validate_operator_and_field_callback=cls._validate_operator_and_field,
            validate_ordering_callback=cls._validate_ordering,
        )

    def _validate(self) -> None:
        errors = []

        for field_name, field_def in self._fields.items():
            try:
                # Get field type from model (implementation depends on ORM)
                field_type = self._get_field_type(field_name)

                # If no operators specified, infer from field type
                if field_def.allowed_operators is None:
                    if issubclass(field_type, Enum | StrEnum | IntEnum):
                        default_operators = DEFAULT_OPERATORS.get(Enum)
                    else:
                        default_operators = DEFAULT_OPERATORS.get(field_type)

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

        if errors:
            raise ValueError("\n".join(errors))

    def _get_field_type(self, field_name: str) -> type:
        """Gets the type of a field - to be implemented by specific ORM builders"""
        return self.builder.get_field_type(field_name)

    @classmethod
    def _validate_operators(cls, field_type: type, operators: set[Operator]) -> set[Operator]:
        """Validates operators against field type"""

        if issubclass(field_type, Enum | StrEnum | IntEnum):
            valid_operators = DEFAULT_OPERATORS.get(Enum)
        else:
            valid_operators = DEFAULT_OPERATORS.get(field_type)

        if not valid_operators:  # pragma: no cover
            return operators

        return {op for op in operators if op not in valid_operators}  # type: ignore

    @classmethod
    def _get_relation_by_alias(cls, alias: str) -> tuple[str, RelationshipRule]:
        relations = {}
        for relation_name, relation_def in cls._relations.items():
            if alias.startswith(relation_def.alias):
                relations[relation_name] = relation_def
        if not relations:
            raise ValueError(f"Relation with alias '{alias}' not found")
        if len(relations) > 1:
            raise ValueError(f"Multiple relations found for alias '{alias}'")
        return list(relations.items())[0]

    @classmethod
    def _get_field_by_alias(cls, alias: str) -> tuple[str, FieldRule]:
        """Gets a field definition by its alias or field name"""
        # First, check local fields
        for field_name, field_def in cls._fields.items():
            if field_def.alias == alias or field_name == alias:
                return field_name, field_def

        relation_name, relation_def = cls._get_relation_by_alias(alias)
        field_to_search = alias.removeprefix(relation_def.alias)[1:]
        field_name, field_def = relation_def.rules._get_field_by_alias(field_to_search)
        return f"{relation_name}.{field_name}", field_def
