import json

from src.domain.value_objects.confirmation_rule import (
    ConfirmationRule,
    ConfirmationRuleType,
    RoleConfirmationRule,
    TeamSizeConfirmationRule,
)


def serialize(rule: ConfirmationRule) -> dict:
    if isinstance(rule, RoleConfirmationRule):
        return {
            "rule_type": rule.rule_type.value,
            "params": {
                "take_into_account_role_count": rule.take_into_account_role_count
            },
        }
    if isinstance(rule, TeamSizeConfirmationRule):
        return {
            "rule_type": rule.rule_type.value,
            "params": {
                "max_team_size": rule.max_team_size,
                "min_team_size": rule.min_team_size,
            },
        }
    raise ValueError(f"Unknown rule type: {type(rule)}")


def deserialize(rule_type: str, params: dict) -> ConfirmationRule:
    if isinstance(params, str):
        params = json.loads(params)

    match ConfirmationRuleType(rule_type):
        case ConfirmationRuleType.ROLE:
            return RoleConfirmationRule(
                take_into_account_role_count=params["take_into_account_role_count"],
            )
        case ConfirmationRuleType.TEAM_SIZE:
            return TeamSizeConfirmationRule(
                max_team_size=params["max_team_size"],
                min_team_size=params["min_team_size"],
            )
        case _:
            raise ValueError(f"Unknown rule type: {rule_type}")
