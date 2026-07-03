from __future__ import annotations

from datetime import datetime, timezone

import pytest

from api.routes.runs import _parse_query_datetime

_EXPECTED_ERROR_SUFFIX = " must be a valid ISO-8601 datetime"


# Part A -- preprocessing semantics (5 axes, NET-NEW vs fo111 D)


class TestPartAPreprocessingSemantics:
    """Strip / case / type / shape contract before ``fromisoformat``."""

    def test_a1_whitespace_character_matrix_short_circuits_to_none(self) -> None:
        whitespace_inputs = ["\t", "\n", "\r\n", "   \t  \n  ", "\v", "\f"]
        for raw in whitespace_inputs:
            assert _parse_query_datetime("created_after", raw) is None, (
                f"whitespace {raw!r} should short-circuit to None"
            )

    def test_a2_lowercase_z_is_not_substituted_key_divergence(self) -> None:
        # Upper-case Z succeeds (already in fo111 D2; repeated here for
        # direct paired contrast with the lowercase arm below).
        upper = _parse_query_datetime("created_after", "2020-01-01T00:00:00Z")
        assert upper == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Lower-case z is NOT substituted -> fromisoformat rejects.
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-01T00:00:00z")
        assert "created_after" in str(exc_info.value)
        assert "ISO-8601" in str(exc_info.value)

    def test_a3_defensive_str_value_wrapping_for_non_string_input(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", 12345)  # type: ignore[arg-type]
        # ValueError (from fromisoformat via the re-raise) -- NOT
        # AttributeError. This is the key pin.
        assert isinstance(exc_info.value, ValueError)
        assert "created_after" in str(exc_info.value)
        # The original cause string contains the coerced value to
        # confirm str(int) flowed through.
        cause = exc_info.value.__cause__
        assert isinstance(cause, ValueError)
        assert "12345" in str(cause)

    def test_a4_bare_date_input_accepted_via_naive_arm(self) -> None:
        result = _parse_query_datetime("created_after", "2020-01-01")
        assert result == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result is not None and result.tzinfo is timezone.utc
        # All time components are zero (midnight).
        assert (
            result.hour == 0
            and result.minute == 0
            and result.second == 0
            and result.microsecond == 0
        )

    def test_a5_internal_whitespace_strip_happens_before_replace(self) -> None:
        result = _parse_query_datetime("created_after", "  2020-01-01T00:00:00Z  ")
        assert result == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Also pin with tab/newline boundaries.
        result_tabs = _parse_query_datetime("created_before", "\t2020-06-15T12:34:56Z\n")
        assert result_tabs == datetime(2020, 6, 15, 12, 34, 56, tzinfo=timezone.utc)


# Part B -- invalid calendar matrix (5 axes)


class TestPartBInvalidCalendarMatrix:
    """Calendar-impossible inputs raise without rollover / clamping."""

    def test_b1_month_greater_than_12_raises_no_rollover(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-13-01")
        assert "created_after" in str(exc_info.value)
        assert "ISO-8601" in str(exc_info.value)

    def test_b2_day_greater_than_31_raises_no_rollover(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-32")
        assert "created_after" in str(exc_info.value)

    def test_b3_day_zero_raises_no_underflow(self) -> None:
        """B3: day 0 raises (no underflow to last-day-of-prev-month).

        Pins that ``"2020-01-00"`` is NOT interpreted as 2019-12-31.
        """
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-00")
        assert "created_after" in str(exc_info.value)

    def test_b4_feb_30_raises_regardless_of_leap_year(self) -> None:
        """B4: Feb 30 is impossible in every year (leap or not).

        Distinct from B5 which contrasts Feb 29 across leap-year arms.
        """
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-02-30")
        assert "created_after" in str(exc_info.value)

        # Same on a non-leap year.
        with pytest.raises(ValueError) as exc_info_b:
            _parse_query_datetime("created_after", "2021-02-30")
        assert "created_after" in str(exc_info_b.value)

    def test_b5_leap_year_arithmetic_real_rules_key_divergence(self) -> None:
        # Leap year (divisible by 4, not 100).
        result_2020 = _parse_query_datetime("created_after", "2020-02-29")
        assert result_2020 == datetime(2020, 2, 29, 0, 0, 0, tzinfo=timezone.utc)

        # Non-leap year (not divisible by 4) -- raises.
        with pytest.raises(ValueError) as exc_2021:
            _parse_query_datetime("created_after", "2021-02-29")
        assert "created_after" in str(exc_2021.value)

        # Century leap year (divisible by 400) -- valid.
        result_2000 = _parse_query_datetime("created_after", "2000-02-29")
        assert result_2000 == datetime(2000, 2, 29, 0, 0, 0, tzinfo=timezone.utc)

        # Century non-leap year (divisible by 100, not 400) -- raises.
        with pytest.raises(ValueError) as exc_1900:
            _parse_query_datetime("created_after", "1900-02-29")
        assert "created_after" in str(exc_1900.value)


# Part C -- invalid time / offset / microsecond matrix (5 axes)


class TestPartCInvalidTimeMatrix:
    """Time-component and offset overflows raise; fractional seconds parse."""

    def test_c1_hour_greater_than_23_raises(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-01T25:00:00")
        assert "created_after" in str(exc_info.value)
        assert "ISO-8601" in str(exc_info.value)

    def test_c2_minute_greater_than_59_raises(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-01T00:60:00")
        assert "created_after" in str(exc_info.value)

    def test_c3_second_60_raises_no_leap_second_acceptance(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-01T00:00:60")
        assert "created_after" in str(exc_info.value)

    def test_c4_offset_hour_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "2020-01-01T00:00:00+25:00")
        assert "created_after" in str(exc_info.value)

    def test_c5_fractional_seconds_and_max_microsecond_boundary(self) -> None:
        result = _parse_query_datetime("created_after", "2020-01-01T00:00:00.123456")
        assert result is not None
        assert result == datetime(2020, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
        assert result.microsecond == 123456

        # Max microsecond -- 999999 boundary.
        result_max = _parse_query_datetime("created_after", "2020-01-01T00:00:00.999999")
        assert result_max is not None
        assert result_max.microsecond == 999999
        assert result_max == datetime(2020, 1, 1, 0, 0, 0, 999999, tzinfo=timezone.utc)


# Part D -- error-message / exception-chain / field-interpolation (5 axes)


class TestPartDErrorChainAndFieldInterpolation:
    """``raise ... from exc`` chain + raw f-string ``{field}`` interpolation."""

    def test_d1_created_after_field_literal_in_message(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "not-a-date")
        assert str(exc_info.value) == "created_after" + _EXPECTED_ERROR_SUFFIX

    def test_d2_created_before_field_literal_in_message(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_before", "not-a-date")
        assert str(exc_info.value) == "created_before" + _EXPECTED_ERROR_SUFFIX

        # And critically, the two messages DIFFER -- a refactor that
        # accidentally shadowed `field` with a constant would collapse
        # them.
        with pytest.raises(ValueError) as exc_info_after:
            _parse_query_datetime("created_after", "not-a-date")
        assert str(exc_info.value) != str(exc_info_after.value)

    def test_d3_empty_field_produces_leading_space_message_key_divergence(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("", "not-a-date")
        # Message begins with a space because f"{''} must be..." -> " must be...".
        assert str(exc_info.value) == "" + _EXPECTED_ERROR_SUFFIX
        assert str(exc_info.value).startswith(" must be")

    def test_d4_arbitrary_field_no_allowlist_validation(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("custom_xyz_!!!", "not-a-date")
        assert "custom_xyz_!!!" in str(exc_info.value)
        assert str(exc_info.value) == "custom_xyz_!!!" + _EXPECTED_ERROR_SUFFIX

    def test_d5_raise_from_exc_chain_preserved_key_divergence(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            _parse_query_datetime("created_after", "not-a-date")

        cause = exc_info.value.__cause__
        # The chain is preserved (NOT None).
        assert cause is not None
        # The original is itself a ValueError (from datetime.fromisoformat).
        assert isinstance(cause, ValueError)
        # The original message mentions the raw input -- pins that the
        # value flowed all the way to fromisoformat unchanged after
        # strip and Z-substitution (neither of which transform
        # "not-a-date").
        assert "not-a-date" in str(cause)
        # The outer message is OUR message, not the inner one -- pins
        # that we wrap rather than re-raise.
        assert "not-a-date" not in str(exc_info.value)
        assert "ISO-8601" in str(exc_info.value)
