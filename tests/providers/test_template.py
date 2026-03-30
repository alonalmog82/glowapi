from utils.providers.template import apply_substitutions, derive_sidecar_path


def test_single_key():
    assert apply_substitutions("hello {{name}}", {"name": "world"}) == "hello world"


def test_multiple_keys():
    assert apply_substitutions("{{a}} and {{b}}", {"a": "foo", "b": "bar"}) == "foo and bar"


def test_missing_key_is_silent():
    result = apply_substitutions("{{key}} stays", {"other": "x"})
    assert result == "{{key}} stays"


def test_extra_key_in_substitutions_is_silent():
    result = apply_substitutions("{{a}}", {"a": "1", "b": "2"})
    assert result == "1"


def test_leaves_hcl_braces_untouched():
    template = 'tags = { Name = "test" }\narn = "${aws_iam_role.main.arn}"'
    assert apply_substitutions(template, {"foo": "bar"}) == template


def test_replaces_all_occurrences():
    assert apply_substitutions("{{x}} {{x}}", {"x": "y"}) == "y y"


def test_empty_substitutions():
    assert apply_substitutions("{{key}}", {}) == "{{key}}"


def test_derive_sidecar_path():
    assert derive_sidecar_path("customers/a.tf") == "customers/a.tf.json"
    assert derive_sidecar_path("a/b/c/file.yaml") == "a/b/c/file.yaml.json"
    assert derive_sidecar_path("file.tf") == "file.tf.json"
