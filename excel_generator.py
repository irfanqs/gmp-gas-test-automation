"""Create GMP gas-test Excel workbooks and matching downloadable chart files."""

import math
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
import xlsxwriter

from config import MOISTURE_LIMIT, OIL_LIMIT, PARTICLE_LIMITS, TEST_TYPES


def _configure_korean_font():
    """Use an installed Korean font for PNG/PDF exports when one is available."""
    for family in ("Apple SD Gothic Neo", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR"):
        try:
            font_manager.findfont(family, fallback_to_default=False)
            plt.rcParams["font.family"] = family
            plt.rcParams["axes.unicode_minus"] = False
            return
        except ValueError:
            continue


_configure_korean_font()

THICK = 1.5
THIN_BORDER = {"border": 1, "border_color": "#A8B8B4"}
CENTER_FORMAT = {"align": "center", "valign": "vcenter", "text_wrap": True, **THIN_BORDER}
LEFT_FORMAT = {"align": "left", "valign": "vcenter", "text_wrap": True, **THIN_BORDER}
HEADER_FORMAT = {**CENTER_FORMAT, "bold": True, "bg_color": "#D9EAF7", **THIN_BORDER}
TITLE_FORMAT = {"bold": True, "font_size": 16, "align": "center", "valign": "vcenter"}
NOTE_FORMAT = {"text_wrap": True, "valign": "vcenter"}
RED_FORMAT = {"bg_color": "#FF9999"}


def _number(value):
    match = re.search(r"-?[\d,]+(?:\.\d+)?", str(value or ""))
    return float(match.group(0).replace(",", "")) if match else 0.0


def _format_mg_text(value):
    """Normalize OCR spacing for mg/m³ measurements without changing the value."""
    text = str(value or "").strip()
    text = re.sub(r"(?<=\d)\s*mg\s*/\s*m[³3]", " mg/m³", text, flags=re.IGNORECASE)
    text = re.sub(r"(mg/m³)\s*(이하|이상)", r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()


def _date_key(value):
    parts = [int(part) for part in str(value or "0.0.0").replace("-", ".").split(".") if part.isdigit()]
    return tuple((parts + [0, 0, 0])[:3])


def _sorted(records):
    return sorted(records, key=lambda row: _date_key(row.get("performed_date")), reverse=True)


def _criteria_number(text, fallback):
    numbers = [float(value.replace(",", "")) for value in __import__("re").findall(r"\d+(?:\.\d+)?", str(text or ""))]
    return numbers[-1] if numbers else fallback


def _identity_text(value):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").lower())


def _category_identity(row, category_fields):
    grade = _identity_text(row.get("grade")) if "grade" in category_fields else ""
    if "management_number" in category_fields:
        management_number = _identity_text(row.get("management_number"))
        if management_number:
            return grade, "management", management_number
        location = str(row.get("location", ""))
        room_codes = re.findall(r"\(([^)]+)\)", location)
        location_key = _identity_text(room_codes[-1] if room_codes else location)
        return grade, "location", location_key
    return tuple(_identity_text(row.get(field)) for field in category_fields)


def _matrix(records, value_field, category_fields, selected_grades=None):
    filtered = [row for row in records if not selected_grades or row.get("grade") in selected_grades]
    dates = sorted({str(row.get("performed_date", "")) for row in filtered}, key=_date_key, reverse=True)
    category_map = {}
    for row in filtered:
        category = tuple(str(row.get(field, "")) for field in category_fields)
        category_map.setdefault(_category_identity(row, category_fields), category)
    categories = list(category_map.values())
    values = {}
    for identity, category in category_map.items():
        for date in dates:
            matches = [
                _number(row.get(value_field)) for row in filtered
                if _category_identity(row, category_fields) == identity
                and str(row.get("performed_date", "")) == date
            ]
            values[(category, date)] = sum(matches) / len(matches) if matches else None
    return categories, dates, values


def _round_up(value, unit):
    return max(unit, math.ceil(value / unit) * unit)


def _chart_major_unit(y_max):
    if y_max <= 1:
        return 0.2
    magnitude = 10 ** math.floor(math.log10(y_max))
    return max(magnitude / 10, math.ceil((y_max / 5) / (magnitude / 10)) * (magnitude / 10))


def _add_xlsx_chart(wb, sheet_name, title, categories, dates, values, limits, y_max, y_axis_title, chart_cell="A10"):
    """Write pivot data and create a clustered column + line chart using xlsxwriter."""
    ws = wb.add_worksheet(sheet_name)
    category_width = 1
    ws.set_column(0, 0, 38)
    for col in range(category_width, category_width + len(dates) + len(limits)):
        ws.set_column(col, col, 16)

    header_fmt = wb.add_format({**HEADER_FORMAT})
    category_fmt = wb.add_format({**LEFT_FORMAT})
    value_fmt = wb.add_format({**CENTER_FORMAT})

    start = 0
    ws.write(start, 0, "측정 위치 / 관리번호", header_fmt)
    for offset, date in enumerate(dates, start=category_width):
        ws.write(start, offset, date, header_fmt)
    limit_start = category_width + len(dates)
    for offset, (label, _) in enumerate(limits, start=limit_start):
        ws.write(start, offset, label, header_fmt)

    for row_index, category in enumerate(categories, start=start + 1):
        ws.write(row_index, 0, "\n".join(reversed(category)), category_fmt)
        ws.set_row(row_index, 30)
        for offset, date in enumerate(dates, start=category_width):
            value = values[(category, date)]
            if value is None:
                ws.write_blank(row_index, offset, None, value_fmt)
            else:
                ws.write_number(row_index, offset, value, value_fmt)
        for offset, (_, limit_val) in enumerate(limits, start=limit_start):
            ws.write_number(row_index, offset, limit_val, value_fmt)

    chart = wb.add_chart({"type": "column"})
    last_row = start + len(categories)
    category_range = [sheet_name, start + 1, 0, last_row, category_width - 1]

    for index, date in enumerate(dates):
        chart.add_series({
            "name": date,
            "categories": category_range,
            "values": [sheet_name, start + 1, category_width + index, last_row, category_width + index],
        })

    line_chart = wb.add_chart({"type": "line"})
    for idx, (label, limit_val) in enumerate(limits):
        line_chart.add_series({
            "name": label,
            "categories": category_range,
            "values": [sheet_name, start + 1, limit_start + idx, last_row, limit_start + idx],
            "line": {
                "color": ["#E67E22", "#C00000", "#C07000", "#375623", "#7030A0"][idx % 5],
                "dash_type": "dash",
                "width": 2,
            },
        })
    if limits:
        chart.combine(line_chart)

    chart.set_title({"name": title})
    chart.set_x_axis({
        "name": "측정 위치 / 관리번호",
        "num_font": {"size": 9, "rotation": 0},
    })
    chart.set_y_axis({
        "name": y_axis_title,
        "min": 0,
        "max": y_max,
        "major_unit": _chart_major_unit(y_max),
    })
    chart.set_legend({"position": "right"})
    chart.set_size({"width": min(1600, max(1100, 400 + len(categories) * 140)), "height": 560})
    chart.set_plotarea({"border": {"none": True}})

    ws.insert_chart(chart_cell, chart)
    return ws


def _plot_chart(path, title, categories, dates, values, limits, y_max):
    labels = ["\n".join(category) for category in categories]
    figure, axis = plt.subplots(figsize=(16, 8))
    width = 0.75 / max(len(dates), 1)
    positions = list(range(len(categories)))
    for index, date in enumerate(dates):
        data = [values[(category, date)] or 0 for category in categories]
        axis.bar([position - 0.375 + width / 2 + index * width for position in positions], data, width, label=date)
    for index, (label, limit) in enumerate(limits):
        axis.axhline(limit, color=["#e67e22", "#c00000", "#c07000", "#375623", "#7030a0"][index % 5], linestyle="--", label=label)
    axis.set_title(title, fontweight="bold")
    axis.set_ylim(0, y_max)
    axis.set_xticks(positions, labels, fontsize=8)
    axis.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    axis.grid(axis="y", alpha=.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    return figure


def _write_data_sheet_xlsx(wb, sheet_name, title, headers, records, col_widths, header_row, row_format_fn=None):
    """Write a styled data sheet using xlsxwriter."""
    ws = wb.add_worksheet(sheet_name)
    title_fmt = wb.add_format(TITLE_FORMAT)
    note_fmt = wb.add_format(NOTE_FORMAT)
    center_fmt = wb.add_format(CENTER_FORMAT)
    left_fmt = wb.add_format(LEFT_FORMAT)
    header_fmt = wb.add_format(HEADER_FORMAT)
    red_center = wb.add_format({**CENTER_FORMAT, **THIN_BORDER, "bg_color": "#FF9999"})
    red_left = wb.add_format({**LEFT_FORMAT, **THIN_BORDER, "bg_color": "#FF9999"})

    ws.merge_range(0, 0, 0, len(headers) - 1, title, title_fmt)

    for col, header in enumerate(headers):
        ws.write(header_row - 1, col, header, header_fmt)

    for col_letter, width in col_widths.items():
        col_idx = ord(col_letter) - ord("A")
        ws.set_column(col_idx, col_idx, width)

    for row_offset, record in enumerate(records):
        row_idx = header_row + row_offset
        ws.set_row(row_idx, 20)
        row_vals = row_format_fn(record) if row_format_fn else []
        for col, value in enumerate(row_vals):
            fmt = left_fmt if col in (2, 3, 6) else center_fmt
            if row_format_fn and hasattr(record, "_red_cols") and col in record._red_cols:
                fmt = red_left if col in (2, 3, 6) else red_center
            if isinstance(value, (int, float)):
                ws.write_number(row_idx, col, value, fmt)
            else:
                ws.write(row_idx, col, value, fmt)

    ws.freeze_panes(header_row, 0)
    return ws


def _generate_oil_or_moisture(test_type, records, output_path, chart_paths):
    is_oil = test_type == "oil"
    title = "유분 측정 일지" if is_oil else "수분 측정 일지"
    chart_title = "오일 함량 측정 기록 피벗 차트" if is_oil else "수분 측정 일지 피벗 차트"
    fallback = OIL_LIMIT if is_oil else MOISTURE_LIMIT
    header_row = 4 if is_oil else 3

    wb = xlsxwriter.Workbook(str(output_path))

    # --- Sheet 1: 데이터 ---
    headers = ["No.", "관리번호", "측정 위치", "점검결과 (mg/m³)", "측정사진 첨부", "판정", "허용기준", "Performed Date"]
    data_ws = wb.add_worksheet("데이터")
    title_fmt = wb.add_format(TITLE_FORMAT)
    header_fmt = wb.add_format(HEADER_FORMAT)
    center_fmt = wb.add_format(CENTER_FORMAT)
    left_fmt = wb.add_format(LEFT_FORMAT)
    red_center = wb.add_format({**CENTER_FORMAT, **THIN_BORDER, "bg_color": "#FF9999"})
    red_left = wb.add_format({**LEFT_FORMAT, **THIN_BORDER, "bg_color": "#FF9999"})

    data_ws.merge_range(0, 0, 0, len(headers) - 1, title, title_fmt)
    for col, header in enumerate(headers):
        data_ws.write(header_row - 1, col, header, header_fmt)

    col_widths = {"A": 8, "B": 14, "C": 28, "D": 22, "E": 16, "F": 12, "G": 42, "H": 16}
    for letter, w in col_widths.items():
        data_ws.set_column(ord(letter) - 65, ord(letter) - 65, w)

    for row_offset, record in enumerate(_sorted(records)):
        row_idx = header_row + row_offset
        vals = [record.get("no"), record.get("management_number"), record.get("location"),
                _format_mg_text(record.get("result_text")), record.get("photo_attached"), record.get("judgement"),
                _format_mg_text(record.get("criteria_text")), record.get("performed_date")]
        exceed = _number(record.get("result_text")) > fallback
        bad_judge = record.get("judgement") != "적합"
        for col, value in enumerate(vals):
            if col in (2, 3, 6):
                fmt = left_fmt
            else:
                fmt = center_fmt
            if (col == 3 and exceed) or (col == 5 and bad_judge):
                fmt = red_left if col in (2, 3, 6) else red_center
            data_ws.write(row_idx, col, value or "", fmt)

    data_ws.freeze_panes(header_row, 0)

    # --- Sheet 2: 간소화된 데이터 ---
    simple_headers = ["No.", "관리번호", "측정 위치", "점검결과 (mg/m³)", "허용기준", "Performed Date"]
    simple_ws = wb.add_worksheet("간소화된 데이터")
    simple_ws.merge_range(0, 0, 0, len(simple_headers) - 1, title, title_fmt)
    for col, header in enumerate(simple_headers):
        simple_ws.write(header_row - 1, col, header, header_fmt)

    simple_widths = {"A": 8, "B": 14, "C": 28, "D": 22, "E": 16, "F": 16}
    for letter, w in simple_widths.items():
        simple_ws.set_column(ord(letter) - 65, ord(letter) - 65, w)

    for row_offset, record in enumerate(_sorted(records)):
        row_idx = header_row + row_offset
        vals = [record.get("no"), record.get("management_number"), record.get("location"),
                _number(record.get("result_text")), _criteria_number(record.get("criteria_text"), fallback),
                record.get("performed_date")]
        for col, value in enumerate(vals):
            fmt = left_fmt if col == 2 else center_fmt
            if isinstance(value, (int, float)):
                simple_ws.write_number(row_idx, col, value, fmt)
            else:
                simple_ws.write(row_idx, col, value or "", fmt)

    simple_ws.freeze_panes(header_row, 0)

    # --- Sheet 3: 피벗 차트 ---
    categories, dates, matrix_values = _matrix(_sorted(records), "result_text", ("management_number", "location"))
    limits = [(f"허용기준 ≤ {_criteria_number(record.get('criteria_text'), fallback):g}", _criteria_number(record.get("criteria_text"), fallback)) for record in _sorted(records)]
    limits = list(dict.fromkeys(limits))
    y_max = _round_up(max([value or 0 for value in matrix_values.values()] + [value for _, value in limits]), 1 if is_oil else 10)
    _add_xlsx_chart(
        wb,
        "피벗 차트",
        chart_title,
        categories,
        dates,
        matrix_values,
        limits,
        y_max,
        "점검결과 (mg/m³)",
        chart_cell="F2",
    )

    wb.close()

    # matplotlib PNG/PDF charts
    figure = _plot_chart(chart_paths[0], chart_title, categories, dates, matrix_values, limits, y_max)
    return [figure]


def _generate_airborne(records, output_path, chart_paths):
    wb = xlsxwriter.Workbook(str(output_path))
    title_fmt = wb.add_format(TITLE_FORMAT)
    note_fmt = wb.add_format(NOTE_FORMAT)
    header_fmt = wb.add_format(HEADER_FORMAT)
    center_fmt = wb.add_format(CENTER_FORMAT)
    left_fmt = wb.add_format(LEFT_FORMAT)
    red_center = wb.add_format({**CENTER_FORMAT, **THIN_BORDER, "bg_color": "#FF9999"})
    red_left = wb.add_format({**LEFT_FORMAT, **THIN_BORDER, "bg_color": "#FF9999"})

    # --- Sheet 1: 데이터 ---
    note = "허용기준 :\n- Grade A: 0.5μm 이상 입자수: 23개/m³ 이하, 5μm 이상 입자수: 4개/m³ 이하\n- Grade B: 0.5μm 이상 입자수: 627개/m³ 이하, 5μm 이상 입자수: 13개/m³ 이하\n- Grade C: 0.5μm 이상 입자수: 23,402개/m³ 이하, 5μm 이상 입자수: 1,540개/m³ 이하\n- Grade D: 0.5μm 이상 입자수: 141,390개/m³ 이하, 5μm 이상 입자수: 8,183개/m³ 이하"
    headers = ["No.", "관리번호", "측정 위치", "Grade", "0.5 μm 이상 부유입자 수/m³", "5.0 μm 이상 부유입자 수/m³", "판정", "Performed Date"]
    headers += [f"{grade} Grade 경고기준 (0.5㎛)" for grade in "ABCD"]
    headers += [f"{grade} Grade 경고기준 (5.0㎛)" for grade in "ABCD"]

    data_ws = wb.add_worksheet("데이터")
    data_ws.merge_range(0, 0, 0, len(headers) - 1, "부유입자 측정 일지", title_fmt)
    data_ws.merge_range(1, 0, 1, len(headers) - 1, note, note_fmt)
    data_ws.set_row(1, 72)
    for col, header in enumerate(headers):
        data_ws.write(4, col, header, header_fmt)

    col_widths = {"A": 8, "B": 14, "C": 28, "D": 9, "E": 24, "F": 24, "G": 12, "H": 16}
    for letter, w in col_widths.items():
        data_ws.set_column(ord(letter) - 65, ord(letter) - 65, w)
    for col_idx in range(8, 16):
        data_ws.set_column(col_idx, col_idx, 20)

    for row_offset, record in enumerate(_sorted(records)):
        row_idx = 5 + row_offset
        grade = str(record.get("grade", "")).upper()
        p05 = _number(record.get("particle_05"))
        p50 = _number(record.get("particle_50"))
        vals = [record.get("no"), record.get("management_number"), record.get("location"),
                record.get("grade"), p05, p50, record.get("judgement"), record.get("performed_date")]
        vals += [PARTICLE_LIMITS["0.5"][g] for g in "ABCD"]
        vals += [PARTICLE_LIMITS["5.0"][g] for g in "ABCD"]
        for col, value in enumerate(vals):
            fmt = left_fmt if col == 2 else center_fmt
            if (col == 4 and p05 > PARTICLE_LIMITS["0.5"].get(grade, math.inf)) or \
               (col == 5 and p50 > PARTICLE_LIMITS["5.0"].get(grade, math.inf)) or \
               (col == 6 and record.get("judgement") != "적합"):
                fmt = red_left if col == 2 else red_center
            if isinstance(value, (int, float)):
                data_ws.write_number(row_idx, col, value, fmt)
            else:
                data_ws.write(row_idx, col, value or "", fmt)

    data_ws.freeze_panes(5, 0)

    # --- Chart sheets ---
    latest_date = max((_date_key(record.get("performed_date")) for record in records), default=(0, 0, 0))
    selected_grades = {"A", "B"} if latest_date[1] == 2 else None
    figures = []
    for particle_size, field, sheet_name, chart_title, image_path in [
        ("0.5", "particle_05", "Pivot 0.5", "PivotChart 0.5 ㎛", chart_paths[0]),
        ("5.0", "particle_50", "Pivot 5.0", "PivotChart 5.0 ㎛", chart_paths[1]),
    ]:
        categories, dates, matrix_values = _matrix(_sorted(records), field, ("grade", "management_number", "location"), selected_grades)
        grades = list(dict.fromkeys(category[0] for category in categories))
        limits = [(f"{grade} Grade 경고기준 = {PARTICLE_LIMITS[particle_size][grade]:,}", PARTICLE_LIMITS[particle_size][grade]) for grade in grades if grade in PARTICLE_LIMITS[particle_size]]
        y_max = _round_up(max([value or 0 for value in matrix_values.values()] + [value for _, value in limits]), 10)
        _add_xlsx_chart(
            wb,
            sheet_name,
            chart_title,
            categories,
            dates,
            matrix_values,
            limits,
            y_max,
            f"{particle_size} μm 이상 부유입자 수/m³",
            chart_cell=f"A{len(categories) + 4}",
        )
        figures.append(_plot_chart(image_path, chart_title, categories, dates, matrix_values, limits, y_max))

    wb.close()
    return figures


def generate_workbook(test_type, records, output_dir, job_id):
    """Generate Excel, PNG charts, and a single PDF containing all charts."""
    output_dir = Path(output_dir)
    chart_paths = [output_dir / f"{job_id}_{test_type}_chart.png"]
    if test_type == "airborne":
        chart_paths = [
            output_dir / f"{job_id}_airborne_pivot_05.png",
            output_dir / f"{job_id}_airborne_pivot_50.png",
        ]
    excel_path = output_dir / f"{job_id}_{TEST_TYPES[test_type]['filename']}"
    if test_type in ("oil", "moisture"):
        figures = _generate_oil_or_moisture(test_type, records, excel_path, chart_paths)
    else:
        figures = _generate_airborne(records, excel_path, chart_paths)
    pdf_path = output_dir / f"{job_id}_{test_type}_charts.pdf"
    with PdfPages(pdf_path) as pdf:
        for figure in figures:
            pdf.savefig(figure)
            plt.close(figure)
    return {"excel": excel_path, "charts": chart_paths, "pdf": pdf_path}
