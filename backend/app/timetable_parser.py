"""Parse weekly timetable HTML exported by the source used as reference.

The expected document is a table whose columns are weekdays and whose rows
are one-hour time slots. Course cells may span multiple rows. Each cell is
expected to contain: course code, course name, teacher, location, and an
optional week range such as "(Week 1-14)".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import time, timedelta
from pathlib import Path

from bs4 import BeautifulSoup, Tag

WEEKDAY_BY_LABEL = {
    "monday": 1,
    "mon": 1,
    "tuesday": 2,
    "tue": 2,
    "tues": 2,
    "wednesday": 3,
    "wed": 3,
    "thursday": 4,
    "thu": 4,
    "thur": 4,
    "thurs": 4,
    "friday": 5,
    "fri": 5,
    "saturday": 6,
    "sat": 6,
    "sunday": 7,
    "sun": 7,
    "星期一": 1,
    "周一": 1,
    "星期二": 2,
    "周二": 2,
    "星期三": 3,
    "周三": 3,
    "星期四": 4,
    "周四": 4,
    "星期五": 5,
    "周五": 5,
    "星期六": 6,
    "周六": 6,
    "星期日": 7,
    "星期天": 7,
    "周日": 7,
    "周天": 7,
}

TIME_RE = re.compile(
    r"^(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)?\s*"
    r"[-–—~]\s*"
    r"(\d{1,2})(?:[.:](\d{2}))?\s*(am|pm)?$",
    re.IGNORECASE,
)
WEEK_RANGE_RE = re.compile(
    r"(?:weeks?|wk|第)\s*(\d{1,2})\s*(?:[-–—~]|to|至)\s*(\d{1,2})\s*周?",
    re.IGNORECASE,
)
WEEK_SINGLE_RE = re.compile(
    r"(?:week|wk)\s*(\d{1,2})",
    re.IGNORECASE,
)


class TimetableParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedCourse:
    weekday: int
    start_time: time
    end_time: time
    course_code: str
    course_name: str
    teacher: str | None
    location: str | None
    week_start: int | None
    week_end: int | None


@dataclass
class ParsedTimetable:
    sessions: list[ParsedCourse] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_timetable_html(content: bytes | str) -> ParsedTimetable:
    soup = BeautifulSoup(content, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise TimetableParseError("HTML 中未找到表格元素")

    best: ParsedTimetable | None = None
    table_errors: list[str] = []

    for table_index, table in enumerate(tables, start=1):
        try:
            parsed = _parse_table(table, table_index)
        except TimetableParseError as exc:
            table_errors.append(str(exc))
            continue
        if not parsed.sessions:
            continue
        if best is None or len(parsed.sessions) > len(best.sessions):
            best = parsed

    if best is None:
        detail = "；".join(table_errors) if table_errors else "未找到有效课程单元格"
        raise TimetableParseError(f"无法识别课表：{detail}")

    best.sessions.sort(
        key=lambda item: (item.weekday, item.start_time, item.course_code)
    )
    return best


def _parse_table(table: Tag, table_index: int) -> ParsedTimetable:
    rows = table.find_all("tr")
    header = _find_header(rows)
    if header is None:
        raise TimetableParseError(f"第 {table_index} 个表格缺少“时间/星期”表头")

    header_row, header_labels = header
    time_column = next(
        (
            index
            for index, label in enumerate(header_labels)
            if _normalize_label(label).lower() in {"time", "时间", "节次"}
        ),
        None,
    )
    if time_column is None:
        raise TimetableParseError(f"第 {table_index} 个表格缺少时间列")

    day_columns = {
        index: weekday
        for index, label in enumerate(header_labels)
        if (weekday := _weekday_number(label)) is not None
    }
    if not day_columns:
        raise TimetableParseError(f"第 {table_index} 个表格缺少星期列")

    header_position = rows.index(header_row)
    body_rows = rows[header_position + 1 :]
    if not body_rows:
        raise TimetableParseError(f"第 {table_index} 个表格没有课程行")

    matrix, cells = _build_cell_matrix(body_rows)
    row_times: dict[int, tuple[time, time]] = {}
    for row_index in range(len(body_rows)):
        time_cell = matrix.get((row_index, time_column))
        if time_cell is None:
            continue
        parsed_time = _parse_time_range(time_cell.get_text(" ", strip=True))
        if parsed_time is not None:
            row_times[row_index] = parsed_time

    result = ParsedTimetable()
    for row_index, column_index, cell, rowspan, _colspan in cells:
        stripped_strings = list(cell.stripped_strings)
        if not stripped_strings:
            continue
        weekday = day_columns.get(column_index)
        if weekday is None:
            continue

        start_time = row_times.get(row_index, (None, None))[0]
        end_time = _resolve_end_time(row_times, row_index, rowspan, start_time)
        if start_time is None or end_time is None or end_time <= start_time:
            result.warnings.append(
                f"{_weekday_name(weekday)}第 {row_index + 1} 行：无法识别课程时间，已跳过"
            )
            continue

        parsed_course = _parse_course_text(
            stripped_strings,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            warnings=result.warnings,
        )
        if parsed_course is not None:
            result.sessions.append(parsed_course)

    return result


def _find_header(rows: list[Tag]) -> tuple[Tag, list[str]] | None:
    best: tuple[Tag, list[str]] | None = None
    best_day_count = 0

    for row in rows:
        cells = row.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        labels: list[str] = []
        for cell in cells:
            label = _normalize_label(cell.get_text(" ", strip=True))
            colspan = _positive_int(cell.get("colspan"), default=1)
            labels.extend([label] * colspan)

        day_count = sum(1 for label in labels if _weekday_number(label) is not None)
        has_time = any(
            _normalize_label(label).lower() in {"time", "时间", "节次"}
            for label in labels
        )
        if has_time and day_count >= 1 and day_count > best_day_count:
            best = (row, labels)
            best_day_count = day_count

    return best


def _build_cell_matrix(
    rows: list[Tag],
) -> tuple[dict[tuple[int, int], Tag], list[tuple[int, int, Tag, int, int]]]:
    matrix: dict[tuple[int, int], Tag] = {}
    cells: list[tuple[int, int, Tag, int, int]] = []

    for row_index, row in enumerate(rows):
        column_index = 0
        for cell in row.find_all(["td", "th"], recursive=False):
            while (row_index, column_index) in matrix:
                column_index += 1
            rowspan = _positive_int(cell.get("rowspan"), default=1)
            colspan = _positive_int(cell.get("colspan"), default=1)
            for row_offset in range(rowspan):
                for column_offset in range(colspan):
                    matrix[(row_index + row_offset, column_index + column_offset)] = (
                        cell
                    )
            cells.append((row_index, column_index, cell, rowspan, colspan))
            column_index += colspan

    return matrix, cells


def _resolve_end_time(
    row_times: dict[int, tuple[time, time]],
    row_index: int,
    rowspan: int,
    start_time: time | None,
) -> time | None:
    if start_time is None:
        return None

    last_row = row_index + max(rowspan, 1) - 1
    for candidate_row in range(last_row, row_index - 1, -1):
        if candidate_row in row_times:
            return row_times[candidate_row][1]

    fallback = timedelta(hours=max(rowspan, 1))
    anchor = timedelta(hours=start_time.hour, minutes=start_time.minute)
    total_minutes = int((anchor + fallback).total_seconds() // 60) % (24 * 60)
    return time(hour=total_minutes // 60, minute=total_minutes % 60)


def _parse_course_text(
    raw_lines: list[str],
    *,
    weekday: int,
    start_time: time,
    end_time: time,
    warnings: list[str],
) -> ParsedCourse | None:
    lines = [_clean_text(line) for line in raw_lines]
    lines = [line for line in lines if line]
    week_start: int | None = None
    week_end: int | None = None

    for index, line in enumerate(lines):
        match = WEEK_RANGE_RE.search(line)
        if match:
            week_start = min(int(match.group(1)), int(match.group(2)))
            week_end = max(int(match.group(1)), int(match.group(2)))
            cleaned = WEEK_RANGE_RE.sub("", line)
            cleaned = re.sub(r"^[\s()（）]+|[\s()（）]+$", "", cleaned).strip()
            if cleaned:
                lines[index] = cleaned
            else:
                del lines[index]
            break

        single_match = WEEK_SINGLE_RE.search(line)
        if single_match:
            week_start = week_end = int(single_match.group(1))
            cleaned = WEEK_SINGLE_RE.sub("", line)
            cleaned = re.sub(r"^[\s()（）]+|[\s()（）]+$", "", cleaned).strip()
            if cleaned:
                lines[index] = cleaned
            else:
                del lines[index]
            break

    if len(lines) < 2:
        warnings.append(
            f"{_weekday_name(weekday)} {start_time.strftime('%H:%M')}："
            "课程单元格缺少课程代码或名称，已跳过"
        )
        return None

    if week_start is not None and not (1 <= week_start <= week_end <= 60):
        warnings.append(
            f"{_weekday_name(weekday)} {start_time.strftime('%H:%M')}："
            f"周次范围 {week_start}-{week_end} 非法，已忽略周次"
        )
        week_start = week_end = None

    if len(lines) > 4:
        warnings.append(
            f"{_weekday_name(weekday)} {start_time.strftime('%H:%M')}："
            f"课程 {lines[0]} 有额外文本行，已忽略：{' / '.join(lines[4:])}"
        )

    return ParsedCourse(
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        course_code=lines[0],
        course_name=lines[1],
        teacher=lines[2] if len(lines) > 2 else None,
        location=lines[3] if len(lines) > 3 else None,
        week_start=week_start,
        week_end=week_end,
    )


def _parse_time_range(value: str) -> tuple[time, time] | None:
    normalized = _normalize_label(value)
    match = TIME_RE.match(normalized)
    if not match:
        return None

    start_hour = int(match.group(1))
    start_minute = int(match.group(2) or 0)
    start_meridiem = match.group(3)
    end_hour = int(match.group(4))
    end_minute = int(match.group(5) or 0)
    end_meridiem = match.group(6)

    if start_meridiem is None and end_meridiem is not None:
        start_meridiem = end_meridiem
    elif end_meridiem is None and start_meridiem is not None:
        end_meridiem = start_meridiem

    try:
        start = time(
            hour=_to_24_hour(start_hour, start_meridiem),
            minute=start_minute,
        )
        end = time(
            hour=_to_24_hour(end_hour, end_meridiem),
            minute=end_minute,
        )
    except ValueError:
        return None

    if end <= start:
        return None
    return start, end


def _to_24_hour(hour: int, meridiem: str | None) -> int:
    if meridiem is None:
        if not 0 <= hour <= 23:
            raise ValueError("invalid hour")
        return hour

    if not 1 <= hour <= 12:
        raise ValueError("invalid 12-hour clock hour")
    if hour == 12:
        hour = 0
    if meridiem.lower() == "pm":
        hour += 12
    return hour


def _weekday_number(label: str) -> int | None:
    normalized = re.sub(r"[.\s]", "", _normalize_label(label)).lower()
    return WEEKDAY_BY_LABEL.get(normalized)


def _normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _clean_text(value: str) -> str:
    return _normalize_label(" ".join(value.replace("\xa0", " ").split()))


def _positive_int(value: str | list[str] | None, *, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _weekday_name(weekday: int) -> str:
    return (
        "周一",
        "周二",
        "周三",
        "周四",
        "周五",
        "周六",
        "周日",
    )[weekday - 1]


def parse_timetable_file(path: str | Path) -> ParsedTimetable:
    """Convenience helper for CLI/manual parsing; API imports use bytes."""
    return parse_timetable_html(Path(path).read_bytes())
