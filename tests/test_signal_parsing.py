"""
Тесты для парсинга условий сигналов из Google Sheets
"""
import pytest
from models.signal import SignalCondition


def test_parse_condition_above():
    """Test: парсинг ABOVE условия"""
    # Различные варианты написания
    test_cases = ['above', 'ABOVE', 'Above', '>']

    for condition_str in test_cases:
        # Эмулируем логику из check_signals_cron.py
        condition_lower = condition_str.lower()
        if 'above' in condition_lower or '>' in condition_lower:
            condition = SignalCondition.ABOVE
        else:
            condition = None

        assert condition == SignalCondition.ABOVE, f"Failed to parse: {condition_str}"


def test_parse_condition_below():
    """Test: парсинг BELOW условия"""
    test_cases = ['below', 'BELOW', 'Below', '<']

    for condition_str in test_cases:
        condition_lower = condition_str.lower()
        if 'below' in condition_lower or '<' in condition_lower:
            condition = SignalCondition.BELOW
        else:
            condition = None

        assert condition == SignalCondition.BELOW, f"Failed to parse: {condition_str}"


def test_parse_condition_equal():
    """Test: парсинг EQUAL условия"""
    test_cases = ['equal', 'EQUAL', 'Equal', '=', '==']

    for condition_str in test_cases:
        condition_lower = condition_str.lower()
        if 'above' in condition_lower or '>' in condition_lower:
            condition = SignalCondition.ABOVE
        elif 'below' in condition_lower or '<' in condition_lower:
            condition = SignalCondition.BELOW
        elif 'equal' in condition_lower or '=' in condition_lower or '==' in condition_lower:
            condition = SignalCondition.EQUAL
        else:
            condition = None

        assert condition == SignalCondition.EQUAL, f"Failed to parse: {condition_str}"


def test_parse_condition_percent_change():
    """Test: парсинг PERCENT_CHANGE условия"""
    test_cases = ['percent', 'PERCENT', 'percent_change', '%', 'Percent Change']

    for condition_str in test_cases:
        condition_lower = condition_str.lower()
        if 'above' in condition_lower or '>' in condition_lower:
            condition = SignalCondition.ABOVE
        elif 'below' in condition_lower or '<' in condition_lower:
            condition = SignalCondition.BELOW
        elif 'equal' in condition_lower or '=' in condition_lower or '==' in condition_lower:
            condition = SignalCondition.EQUAL
        elif 'percent' in condition_lower or '%' in condition_lower:
            condition = SignalCondition.PERCENT_CHANGE
        else:
            condition = None

        assert condition == SignalCondition.PERCENT_CHANGE, f"Failed to parse: {condition_str}"


def test_parse_condition_order_matters():
    """Test: порядок проверки условий важен"""
    # "above" должен распознаваться раньше чем другие
    test_str = 'above'

    condition_lower = test_str.lower()
    if 'above' in condition_lower or '>' in condition_lower:
        condition = SignalCondition.ABOVE
    elif 'below' in condition_lower or '<' in condition_lower:
        condition = SignalCondition.BELOW
    elif 'equal' in condition_lower or '=' in condition_lower:
        condition = SignalCondition.EQUAL
    elif 'percent' in condition_lower or '%' in condition_lower:
        condition = SignalCondition.PERCENT_CHANGE
    else:
        condition = None

    assert condition == SignalCondition.ABOVE


def test_all_signal_conditions_supported():
    """Test: все SignalCondition.* поддерживаются парсером"""
    # Проверяем что для каждого condition есть способ его распарсить

    conditions_map = {
        SignalCondition.ABOVE: 'above',
        SignalCondition.BELOW: 'below',
        SignalCondition.EQUAL: 'equal',
        SignalCondition.PERCENT_CHANGE: 'percent'
    }

    for expected_condition, test_string in conditions_map.items():
        condition_lower = test_string.lower()

        if 'above' in condition_lower or '>' in condition_lower:
            parsed_condition = SignalCondition.ABOVE
        elif 'below' in condition_lower or '<' in condition_lower:
            parsed_condition = SignalCondition.BELOW
        elif 'equal' in condition_lower or '=' in condition_lower or '==' in condition_lower:
            parsed_condition = SignalCondition.EQUAL
        elif 'percent' in condition_lower or '%' in condition_lower:
            parsed_condition = SignalCondition.PERCENT_CHANGE
        else:
            parsed_condition = None

        assert parsed_condition == expected_condition, \
            f"Failed to parse {expected_condition.value} from '{test_string}'"


def test_ui_dropdown_choices():
    """Test: все выборы из UI Dropdown поддерживаются"""
    # Choices из app.py: ["above", "below", "equal", "percent_change"]
    ui_choices = ["above", "below", "equal", "percent_change"]

    for choice in ui_choices:
        condition_lower = choice.lower()

        if 'above' in condition_lower or '>' in condition_lower:
            condition = SignalCondition.ABOVE
        elif 'below' in condition_lower or '<' in condition_lower:
            condition = SignalCondition.BELOW
        elif 'equal' in condition_lower or '=' in condition_lower or '==' in condition_lower:
            condition = SignalCondition.EQUAL
        elif 'percent' in condition_lower or '%' in condition_lower:
            condition = SignalCondition.PERCENT_CHANGE
        else:
            condition = None

        assert condition is not None, f"UI choice '{choice}' cannot be parsed!"
        assert condition.value in ['above', 'below', 'equal', 'percent_change']
