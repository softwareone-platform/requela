# Shared by the SQLAlchemy and Django integration tests: the same RQL pattern must select
# the same user names on every backend.
USER_NAMES = ["Ratatouille", "Rat", "rat", "Remy", "R.tatouille", "Linguini"]

LIKE_CASES = [
    ("Rat", {"Rat"}),
    ("Rat*", {"Ratatouille", "Rat"}),
    ("*ouille", {"Ratatouille", "R.tatouille"}),
    ("*tat*", {"Ratatouille", "R.tatouille"}),
    ("R*y", {"Remy"}),
    ("R.*ouille", {"R.tatouille"}),
]

ILIKE_CASES = [
    ("rat", {"Rat", "rat"}),
    ("RAT*", {"Ratatouille", "Rat", "rat"}),
    ("*OUILLE", {"Ratatouille", "R.tatouille"}),
    ("*TAT*", {"Ratatouille", "R.tatouille"}),
    ("r*Y", {"Remy"}),
]
