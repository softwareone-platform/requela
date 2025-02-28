import logging
from enum import Enum, IntEnum, StrEnum
from typing import Any, ClassVar

from requela.builders import QueryBuilder, get_builder_for_model
from requela.dataclasses import DEFAULT_OPERATORS, FieldDefinition, Operator

logger = logging.getLogger(__name__)


class ModelFilterMeta(type):
    def __new__(mcs, name, bases, namespace):
        if name == "ModelFilter":
            return super().__new__(mcs, name, bases, namespace)

        if "__model__" not in namespace:
            raise ValueError(f"{name} must define __model__")

        fields = {}
        relations = {}

        for key, value in namespace.items():
            if isinstance(value, FieldDefinition):
                fields[key] = value
            elif isinstance(value, ModelFilter):
                relations[key] = value

        namespace["_fields"] = fields
        namespace["_relations"] = relations
        return super().__new__(mcs, name, bases, namespace)


class ModelFilter(metaclass=ModelFilterMeta):
    __model__: ClassVar[Any]  # Type of the model (SQLAlchemy, Django, etc.)
    _fields: ClassVar[dict[str, FieldDefinition]]
    _relations: ClassVar[dict[str, "ModelFilter"]]  # New attribute for relations

    def __init__(self):
        self.builder = self._get_builder()
        self._validate()

    def _get_builder(cls) -> QueryBuilder:
        # from requela.builders.factory import get_builder_for_model
        return get_builder_for_model(
            cls.__model__,
            resolve_alias_callback=cls._resolve_alias,
            validate_operator_and_field_callback=cls._validate_operator_and_field,
        )

    @classmethod
    def _resolve_alias(cls, alias: str) -> str:
        """Resolves alias to actual field path"""
        field_name, _ = cls.get_field_by_alias(alias)
        logger.info(f"[{cls.__name__}] Resolving alias: {alias} to field: {field_name}")
        return field_name

    @classmethod
    def _validate_operator_and_field(cls, field: str, operator: Operator) -> bool:
        _, field_def = cls.get_field_by_alias(field)
        if operator not in field_def.allowed_operators:  # type: ignore
            raise ValueError(f"Operator '{operator.value}' is not allowed for field '{field}'.")
        return True

    def _validate(self) -> None:
        """Validates the filter configuration and infers missing operators"""
        errors = []

        for field_name, field_def in self._fields.items():
            try:
                # Get field type from model (implementation depends on ORM)
                field_type = self._get_field_type(field_name)

                # If no operators specified, infer from field type
                if field_def.allowed_operators is None:
                    logger.info(
                        f"[{self.__class__.__name__}] Inferring operators for "
                        f"field: {field_name} of type: {field_type}"
                    )
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
                if field_def.allowed_operators:
                    logger.info(
                        f"[{self.__class__.__name__}] Validating operators for field: {field_name}"
                    )
                    invalid_ops = self._validate_operators(field_type, field_def.allowed_operators)
                    logger.info(f"[{self.__class__.__name__}] Invalid operators: {invalid_ops}")
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

    def build_query(self, rql_expression: str, initial_query: Any = None) -> Any:
        """Builds the query using the configured builder"""
        return self.builder.build_query(
            rql_expression,
            initial_query=initial_query,
        )

    @classmethod
    def get_field_by_alias(cls, alias: str) -> tuple[str, FieldDefinition]:
        """Gets a field definition by its alias or field name"""
        logger.info(f"Getting field by alias: {alias}")
        # First, check local fields
        for field_name, field_def in cls._fields.items():
            logger.info(
                f"[{cls.__name__}] Checking field: {field_name} for alias: {field_def.alias}"
            )
            if field_def.alias == alias or field_name == alias:
                return field_name, field_def

        # Then, check relations
        if "." in alias:
            relation_name, nested_field = alias.split(".", 1)
            logger.info(
                f"[{cls.__name__}] Checking relation: {relation_name} for alias: {nested_field}"
            )
            if relation_name in cls._relations:
                field_name, field_def = cls._relations[relation_name].get_field_by_alias(
                    nested_field
                )
                return f"{relation_name}.{field_name}", field_def

        raise ValueError(f"Field with alias or name '{alias}' not found")
