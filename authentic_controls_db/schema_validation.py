from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit


def validate_instance(instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    """Validate an instance against the JSON Schema subset used by this project.

    The database tooling intentionally has no third-party runtime dependencies. This
    validator therefore implements the small Draft 2020-12 subset used by the checked-in
    schemas while leaving cross-record and provenance checks to validate.py.
    """

    errors: list[str] = []
    _validate(instance, schema, schema, label, errors)
    return errors


def _validate(
    instance: Any,
    rule: Any,
    root_schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    if rule is True:
        return
    if rule is False:
        errors.append(f"{path}: value is not permitted by schema")
        return
    if not isinstance(rule, dict):
        errors.append(f"{path}: invalid schema rule")
        return

    reference = rule.get("$ref")
    if reference is not None:
        resolved = _resolve_local_reference(root_schema, reference)
        if resolved is None:
            errors.append(f"{path}: unresolved schema reference {reference!r}")
            return
        _validate(instance, resolved, root_schema, path, errors)
        return

    if "not" in rule and _matches(instance, rule["not"], root_schema):
        errors.append(f"{path}: value is disallowed by schema")

    if "const" in rule and instance != rule["const"]:
        errors.append(f"{path}: expected constant value {rule['const']!r}")

    if "enum" in rule and instance not in rule["enum"]:
        errors.append(f"{path}: invalid value {instance!r}; expected one of {rule['enum']!r}")

    expected_type = rule.get("type")
    if expected_type is not None and not _has_type(instance, expected_type):
        errors.append(f"{path}: expected type {_type_label(expected_type)}")
        return

    if isinstance(instance, dict):
        required = rule.get("required", [])
        for name in required:
            if name not in instance:
                errors.append(f"{path}: missing required property {name!r}")

        properties = rule.get("properties", {})
        for name, value in instance.items():
            child_path = f"{path}.{name}"
            if name in properties:
                _validate(value, properties[name], root_schema, child_path, errors)
            elif rule.get("additionalProperties") is False:
                errors.append(f"{child_path}: unexpected property")
            elif isinstance(rule.get("additionalProperties"), dict):
                _validate(
                    value,
                    rule["additionalProperties"],
                    root_schema,
                    child_path,
                    errors,
                )

    if isinstance(instance, list):
        minimum_items = rule.get("minItems")
        if minimum_items is not None and len(instance) < minimum_items:
            errors.append(f"{path}: expected at least {minimum_items} item(s)")
        if rule.get("uniqueItems") and not _items_are_unique(instance):
            errors.append(f"{path}: items must be unique")
        item_rule = rule.get("items")
        if item_rule is not None:
            for index, value in enumerate(instance):
                _validate(value, item_rule, root_schema, f"{path}[{index}]", errors)

    if isinstance(instance, str):
        minimum_length = rule.get("minLength")
        if minimum_length is not None and len(instance) < minimum_length:
            errors.append(f"{path}: expected at least {minimum_length} character(s)")
        pattern = rule.get("pattern")
        if pattern is not None and re.search(pattern, instance) is None:
            errors.append(f"{path}: value does not match pattern {pattern!r}")
        value_format = rule.get("format")
        if value_format == "date" and not _is_date(instance):
            errors.append(f"{path}: expected an ISO date")
        elif value_format == "date-time" and not _is_datetime(instance):
            errors.append(f"{path}: expected an ISO date-time with timezone")
        elif value_format == "uri" and not _is_uri(instance):
            errors.append(f"{path}: expected an absolute URI")

    if _is_number(instance):
        minimum = rule.get("minimum")
        maximum = rule.get("maximum")
        if minimum is not None and instance < minimum:
            errors.append(f"{path}: value must be at least {minimum}")
        if maximum is not None and instance > maximum:
            errors.append(f"{path}: value must be at most {maximum}")


def _matches(instance: Any, rule: Any, root_schema: dict[str, Any]) -> bool:
    candidate_errors: list[str] = []
    _validate(instance, rule, root_schema, "$", candidate_errors)
    return not candidate_errors


def _resolve_local_reference(root_schema: dict[str, Any], reference: Any) -> Any | None:
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return None
    current: Any = root_schema
    for encoded in reference[2:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            return None
        current = current[token]
    return current


def _has_type(instance: Any, expected: str | list[str]) -> bool:
    choices = [expected] if isinstance(expected, str) else expected
    return any(_has_single_type(instance, choice) for choice in choices)


def _has_single_type(instance: Any, expected: str) -> bool:
    if expected == "null":
        return instance is None
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return _is_number(instance)
    return False


def _type_label(expected: str | list[str]) -> str:
    return expected if isinstance(expected, str) else " or ".join(expected)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _items_are_unique(items: list[Any]) -> bool:
    serialized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in items]
    return len(serialized) == len(set(serialized))


def _is_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_uri(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return bool(parsed.scheme and (parsed.netloc or parsed.scheme == "file"))


def _is_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None
