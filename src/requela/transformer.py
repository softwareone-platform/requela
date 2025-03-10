from datetime import date, datetime

from lark import Transformer

from requela.dataclasses import (
    FilterExpression,
    OperatorFunctions,
    OrderByExpression,
    OrderField,
)


class RQLTransformer(Transformer):
    def __init__(self, operators: OperatorFunctions):
        super().__init__()
        self.operators = operators

    def start(self, args):
        return args[0]

    def expression(self, args):
        # Extract the actual operation from the expression node
        return args[0]

    def logical_expression(self, args):
        # apply the logical operator to the list of conditions
        operator_func = args[0]
        argument_list = args[1]
        conditions = [argument.condition for argument in argument_list]
        return FilterExpression(condition=operator_func(*conditions))

    def and_op(self, _):
        return self.operators.and_op

    def or_op(self, _):
        return self.operators.or_op

    def not_op(self, _):
        return self.operators.not_op

    def eq_op(self, _):
        return self.operators.eq_op

    def ne_op(self, _):
        return self.operators.ne_op

    def gt_op(self, _):
        return self.operators.gt_op

    def lt_op(self, _):
        return self.operators.lt_op

    def gte_op(self, _):
        return self.operators.gte_op

    def lte_op(self, _):
        return self.operators.lte_op

    def in_op(self, _):
        return self.operators.in_op

    def out_op(self, _):
        return self.operators.out_op

    def like_op(self, _):
        return self.operators.like_op

    def ilike_op(self, _):
        return self.operators.ilike_op

    def argument_list(self, args):
        return list(args)

    def argument(self, args):
        return args[0]

    def comparison(self, args):
        operator, prop, value = args
        return FilterExpression(
            condition=operator(prop, value),
        )

    def property(self, args):
        return str(args[0])

    def value(self, args):
        # Directly return the processed literal
        return args[0]

    def literal(self, args):
        value = args[0]
        if isinstance(value, str):
            if value == "true":
                return True
            if value == "false":
                return False
            if value == "null()":
                return None
            if value == "empty()":
                return ""
        return value

    def FLOAT(self, token):
        return float(token)

    def INT(self, token):
        return int(token)

    def DATETIME(self, token):
        return datetime.fromisoformat(token)

    def DATE(self, token):
        return date.fromisoformat(token)

    def UNQUOTED_VAL(self, token):
        return str(token)

    def tuple(self, args):
        return tuple(args)

    def any_expression(self, args):
        relationship_name, filter_expression = args
        return FilterExpression(
            condition=self.operators.any_op(relationship_name, filter_expression.condition)
        )

    def order_expression(self, args):
        order_list = args[0]
        return OrderByExpression(fields=order_list)

    def order_list(self, args):
        return list(args)

    def order_item(self, args):
        return OrderField(direction=args[0], field_path=args[1])

    def SIGN(self, token):
        return str(token)

    def combined_expression(self, args):
        # Handle multiple operations
        operations = []
        for arg in args:
            operations.append(arg)
        return operations

    def single_expression(self, args):
        # Extract the actual operation from the single_expression node
        return args[0]
