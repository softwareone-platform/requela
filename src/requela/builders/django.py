from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.db.models.query import QuerySet

from requela.builders.base import QueryBuilder
from requela.dataclasses import FilterExpression, OrderByExpression


@dataclass
class PrefetchExpression:
    relationship_name: str
    condition: Q


class DjangoQueryBuilder(QueryBuilder):
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
        return Q(**{self.resolve_property(prop): value})

    def apply_ne(self, prop: str, value: str | bool | date | datetime | int | float | None) -> Q:
        if value is None:
            return Q(**{f"{self.resolve_property(prop)}__isnull": False})
        return ~Q(**{self.resolve_property(prop): value})

    def apply_gt(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__gt": value})

    def apply_lt(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__lt": value})

    def apply_gte(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__gte": value})

    def apply_lte(self, prop: str, value: date | datetime | int | float) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__lte": value})

    def apply_in(self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]) -> Q:
        return Q(**{f"{self.resolve_property(prop)}__in": value})

    def apply_out(self, prop: str, value: Sequence[str] | Sequence[float] | Sequence[int]) -> Q:
        return ~Q(**{f"{self.resolve_property(prop)}__in": value})

    def apply_like(self, prop: str, value: str) -> Q:
        if value.startswith("*") and value.endswith("*"):
            return Q(**{f"{self.resolve_property(prop)}__contains": value[1:-1]})
        elif value.startswith("*") and not value.endswith("*"):
            return Q(**{f"{self.resolve_property(prop)}__endswith": value[1:]})
        elif not value.startswith("*") and value.endswith("*"):
            return Q(**{f"{self.resolve_property(prop)}__startswith": value[:-1]})
        else:
            return Q(**{f"{self.resolve_property(prop)}__contains": value})

    def apply_ilike(self, prop: str, value: str) -> Q:
        if value.startswith("*") and value.endswith("*"):
            return Q(**{f"{self.resolve_property(prop)}__icontains": value[1:-1]})
        elif value.startswith("*") and not value.endswith("*"):
            return Q(**{f"{self.resolve_property(prop)}__iendswith": value[1:]})
        elif not value.startswith("*") and value.endswith("*"):
            return Q(**{f"{self.resolve_property(prop)}__istartswith": value[:-1]})
        else:
            return Q(**{f"{self.resolve_property(prop)}__icontains": value})

    def resolve_property(self, prop_path: str) -> str:
        prop = self.resolve_alias(prop_path)
        return prop.replace(".", "__")

    def apply_any(self, relationship_name, condition: Q) -> PrefetchExpression:
        return PrefetchExpression(relationship_name, condition)

    def apply_filter(self, query: QuerySet, filter_expression: FilterExpression) -> QuerySet:
        if isinstance(filter_expression.condition, PrefetchExpression):
            query = query.prefetch_related(filter_expression.condition.relationship_name)
            return query.filter(filter_expression.condition.condition)
        return query.filter(filter_expression.condition)

    def apply_joins(self, query: QuerySet):
        return query

    def apply_order_by(self, query: QuerySet, order_by_expression: OrderByExpression) -> QuerySet:
        fields = []
        for order_field in order_by_expression.fields:
            prop = self.resolve_property(order_field.field_path)
            if order_field.direction == "-":
                prop = f"-{prop}"
            fields.append(prop)
        return query.order_by(*fields)
