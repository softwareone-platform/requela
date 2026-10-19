import re
from collections.abc import Callable, Sequence
from datetime import date, datetime
from typing import Any

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Exists, OuterRef, Q
from django.db.models.query import QuerySet

from requela.builders.base import QueryBuilder
from requela.dataclasses import FilterExpression, OrderByExpression


class DjangoQueryBuilder(QueryBuilder):
    def __init__(
        self,
        model_class: Any,
        resolve_alias_callback: Callable | None = None,
        validate_operator_and_field_callback: Callable | None = None,
        validate_ordering_callback: Callable | None = None,
        get_field_rule_callback: Callable | None = None,
    ):
        super().__init__(
            model_class,
            resolve_alias_callback=resolve_alias_callback,
            validate_operator_and_field_callback=validate_operator_and_field_callback,
            validate_ordering_callback=validate_ordering_callback,
            get_field_rule_callback=get_field_rule_callback,
        )
        self.prefetches: list[str] = []

    def get_initial_query(self):
        return self.model_class.objects.all()

    def get_field_type(self, field: str) -> type:
        try:
            django_field = self.model_class._meta.get_field(field)
            if django_field.get_internal_type() == "CharField":
                return str
            elif django_field.get_internal_type() == "DateTimeField":
                return datetime
            elif django_field.get_internal_type() == "DateField":
                return date
            elif django_field.get_internal_type() == "IntegerField":
                return int
            elif django_field.get_internal_type() == "FloatField":
                return float
            elif django_field.get_internal_type() == "BooleanField":
                return bool
            else:
                raise ValueError(f"Unsupported field type: {django_field.get_internal_type()}")
        except FieldDoesNotExist:
            raise AttributeError(
                f"Field '{field}' not found in model '{self.model_class.__name__}'."
            )

    def apply_and(self, *conditions: Q) -> Q:
        query = Q()
        for condition in conditions:
            query &= condition
        return query

    def apply_or(self, *conditions: Q) -> Q:
        query = Q()
        for condition in conditions:
            query |= condition
        return query

    def apply_not(self, condition: Q) -> Q:
        return ~condition

    def apply_eq(self, prop: str, value: str | bool | date | datetime | int | float | None) -> Q:
        if value is None:
            return Q(**{f"{self.resolve_property(prop)}__isnull": True})
        return Q(**{self.resolve_property(prop): self.convert_value(prop, value)})

    def apply_ne(self, prop: str, value: str | bool | date | datetime | int | float | None) -> Q:
        if value is None:
            return Q(**{f"{self.resolve_property(prop)}__isnull": False})
        return ~Q(**{self.resolve_property(prop): self.convert_value(prop, value)})

    def apply_gt(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__gt": self.convert_value(prop, value)})

    def apply_lt(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__lt": self.convert_value(prop, value)})

    def apply_gte(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__gte": self.convert_value(prop, value)})

    def apply_lte(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__lte": self.convert_value(prop, value)})

    def apply_in(self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]) -> Q:
        values = [self.convert_value(prop, item) for item in value]
        return Q(**{f"{self.resolve_property(prop)}__in": values})

    def apply_out(self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]) -> Q:
        values = [self.convert_value(prop, item) for item in value]
        return ~Q(**{f"{self.resolve_property(prop)}__in": values})

    def apply_like(self, prop: str, value: str) -> Q:
        return self.apply_pattern(prop, value, case_insensitive=False)

    def apply_ilike(self, prop: str, value: str) -> Q:
        return self.apply_pattern(prop, value, case_insensitive=True)

    def apply_pattern(self, prop: str, value: str, case_insensitive: bool) -> Q:
        prefix = "i" if case_insensitive else ""
        field = self.resolve_property(prop)
        leading = value.startswith("*")
        trailing = len(value) > 1 and value.endswith("*")
        text = value[1 if leading else None : -1 if trailing else None]

        if "*" in text:
            # Wildcards in the middle: no lookup fits, use an anchored regex
            regex = "^" + ".*".join(re.escape(part) for part in value.split("*")) + "$"
            return Q(**{f"{field}__{prefix}regex": regex})
        if leading and trailing:
            return Q(**{f"{field}__{prefix}contains": text})
        if leading:
            return Q(**{f"{field}__{prefix}endswith": text})
        if trailing:
            return Q(**{f"{field}__{prefix}startswith": text})
        return Q(**{f"{field}__{prefix}exact": text})

    def resolve_property(self, prop_path: str) -> str:
        prop = self.resolve_alias(prop_path)
        return prop.replace(".", "__")

    def apply_any(self, relationship_name, condition: Q) -> Q:
        relationship_name = self.resolve_alias(relationship_name)
        relationship = self.model_class._meta.get_field(relationship_name)
        related_rows = relationship.related_model.objects.filter(
            **{relationship.remote_field.name: OuterRef("pk")}
        ).filter(self._relative_condition(condition, f"{relationship_name}__"))
        if relationship_name not in self.prefetches:
            self.prefetches.append(relationship_name)
        return Q(Exists(related_rows))

    def _relative_condition(self, condition: Q, prefix: str) -> Q:
        children = []
        for child in condition.children:
            if isinstance(child, Q):
                children.append(self._relative_condition(child, prefix))
            elif isinstance(child, tuple) and child[0].startswith(prefix):
                children.append((child[0].removeprefix(prefix), child[1]))
            elif isinstance(child, tuple):
                relationship = prefix.removesuffix("__")
                raise ValueError(
                    f"Field '{child[0].replace('__', '.')}' is not part of "
                    f"relationship '{relationship}'."
                )
            else:
                raise ValueError("Nested any() is not supported.")
        return Q(*children, _connector=condition.connector, _negated=condition.negated)

    def apply_filter(self, query: QuerySet, filter_expression: FilterExpression) -> QuerySet:
        return query.filter(filter_expression.condition)

    def apply_joins(self, query: QuerySet):
        if self.prefetches:
            query = query.prefetch_related(*self.prefetches)
        return query

    def build_query(self, rql_query: str, initial_query: Any = None) -> Any:
        self.prefetches = []
        return super().build_query(rql_query=rql_query, initial_query=initial_query)

    def apply_order_by(self, query: QuerySet, order_by_expression: OrderByExpression) -> QuerySet:
        fields = []
        for order_field in order_by_expression.fields:
            prop = self.resolve_property(order_field.field_path)
            if order_field.direction == "-":
                prop = f"-{prop}"
            fields.append(prop)
        return query.order_by(*fields)
