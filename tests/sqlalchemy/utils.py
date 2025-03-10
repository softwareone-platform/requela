def assert_statements_equal(stmt, expected):
    compiled = stmt.compile()
    expected_compiled = expected.compile()
    assert str(compiled.string) == str(expected_compiled.string), (
        f"\nSQL Statement differs:\nActual:\n{compiled.string}\n"
        f"Expected:\n{expected_compiled.string}"
    )

    # Compare parameters with better formatting for pytest output
    assert compiled.params == expected_compiled.params, (
        f"\nSQL Parameters differ:\nActual:\n{compiled.params}\n"
        f"Expected:\n{expected_compiled.params}"
    )
