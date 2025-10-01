from typing import Callable

from models import Record


class Validator:
    def __init__(self) -> None:
        self.rules: list[Callable[[Record], bool]] = []

    def add_rule(self, rule: Callable[[Record], bool]) -> None:
        self.rules.append(rule)

    def validate(self, record: Record) -> bool:
        return all(rule(record) for rule in self.rules)

    def validate_batch(self, records: list[Record]) -> list[bool]:
        return [self.validate(record) for record in records]


def min_length(field: str, length: int) -> Callable[[Record], bool]:
    def rule(record: Record) -> bool:
        value = getattr(record, field, "")
        return len(value) >= length

    return rule


def max_length(field: str, length: int) -> Callable[[Record], bool]:
    def rule(record: Record) -> bool:
        value = getattr(record, field, "")
        return len(value) <= length

    return rule


def required_fields(*fields: str) -> Callable[[Record], bool]:
    def rule(record: Record) -> bool:
        for field in fields:
            value = getattr(record, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                return False
        return True

    return rule


def no_forbidden_words(field: str, words: list[str]) -> Callable[[Record], bool]:
    def rule(record: Record) -> bool:
        value = getattr(record, field, "").lower()
        return not any(word.lower() in value for word in words)

    return rule
