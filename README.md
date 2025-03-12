[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_requela&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_requela) [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=softwareone-platform_requela&metric=coverage)](https://sonarcloud.io/summary/new_code?id=softwareone-platform_requela) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/requela)](https://pypi.org/project/requela/)


![ReQueLa](https://raw.githubusercontent.com/softwareone-platform/requela/main/assets/requela_logo.png)

# ReQueLa, your data assistant!

## What is ReQueLa?

ReQueLa is a Python library that allows you to build complex queries to filter and order data in your database.
Query are written using RQL, Resource Query Language, a query language expecially designed for RESTful resources.


## Installation

```bash
pip install requela
```

## Supported RQL operators

| Syntax | Explanation |
| --- | --- |
| `eq(field,value)` | Equal to |
| `ne(field,value)` | Not Equal to |
| `gt(field,value)` | Greater Than |
| `gte(field,value)` | Greater Than or Equal |
| `lt(field,value)` | Less Than |
| `lte(field,value)` | Less Than or Equal |
| `in(field,(value1,value2,...))` | In list |
| `out(field,(value1,value2,...))` | Not In list |
| `like(field,value)` | Like |
| `ilike(field,value)` | Case-insensitive Like |
| `and(expression1,expression2,...)` | Logical AND |
| `or(expression1,expression2,...)` | Logical OR |
| `not(expression)` | Logical NOT |
| `any(relationship,expression)` | ANY operator for to-many relationships |
| `order_by(field1,field2,...)` | Order By fields |

### Examples
* Filtering: `and(eq(name,John),gt(age,30))`
* Navigation through relationships using dot notation: `eq(account.name,My Account)` to filter on a related field.
* Filtering with ANY operator: `any(users,eq(users.name,John))`
* Ordering: `order_by(name,age)`
* To order in descendant order, prefix the property name with a minus sign: `order_by(-age)`
* Combining filtering and ordering: `and(eq(name,John),gt(age,30))&order_by(name,age)`
* Using logical operators: `or(eq(name,John),eq(name,Jane))&order_by(name)`
* Using NOT operator: `not(eq(name,John))&order_by(name)`
* Using LIKE operator with wildcard symbol *: `like(name,*John*)`
* Using ILIKE operator with wildcard symbol *: `ilike(name,*John*)`

## Usage

### Use QueryBuilder directly

#### SQLAlchemy

```python
from requela import get_builder_for_model

from app.db import get_session
from app.models import MyModel

builder = get_builder_for_model(MyModel)
statement = builder.build_query("and(eq(name,John),gt(age,30))&order_by(name,-age)")

with get_session() as session:
    result = session.execute(statement)
    for model in result:
        print(model)
```

#### Django

```python
from requela import get_builder_for_model

from app.models import MyModel

builder = get_builder_for_model(MyModel)
result = builder.build_query("and(eq(name,John),gt(age,30))&order_by(name,-age)")

for model in result:
    print(model)
```

### Create a ModelRQLRules class

You can create a class to specify filtering and ordering rules for a given model like:

```python
from requela import FieldRule, ModelRQLRules, Operator, RelationshipRules
from tests.django.models import Account, User


class AccountRules(ModelRQLRules):
    __model__ = Account

    name = FieldRule()
    description = FieldRule()
    status = FieldRule()
    balance = FieldRule()
    created_at = FieldRule(
        alias="events.created.at",
    )


class UserRules(ModelRQLRules):
    __model__ = User

    name = FieldRule()
    age = FieldRule()
    role = FieldRule(
        allowed_operators=[Operator.IN, Operator.OUT],
    )
    is_active = FieldRule(allow_ordering=False)
    birth_date = FieldRule(
        alias="events.born.at",
    )
    account = RelationshipRules(rules=AccountRules())

    rules = UserRules()
    query = rules.build_query("and(eq(name,John),gt(age,30),eq(events.born.at,2024-01-01))&order_by(name,-age)")
```




## License

ReQueLa is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0) and is copyright SoftwareOne AG.

