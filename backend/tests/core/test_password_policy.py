from app.core.password_policy import validate_password


def test_valid_password():
    assert validate_password("Test1234") == []


def test_too_short():
    errors = validate_password("Te1")
    assert any("8 characters" in e for e in errors)


def test_no_uppercase():
    errors = validate_password("test1234")
    assert any("uppercase" in e for e in errors)


def test_no_lowercase():
    errors = validate_password("TEST1234")
    assert any("lowercase" in e for e in errors)


def test_no_digit():
    errors = validate_password("Testtest")
    assert any("digit" in e for e in errors)
