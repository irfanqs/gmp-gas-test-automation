"""Parsers for the three GMP gas-test forms returned by DeepSeek-OCR."""

import re
from html.parser import HTMLParser


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.rowspan, self.colspan = 1, 1

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            attributes = dict(attrs)
            self.cell = []
            self.rowspan = int(attributes.get("rowspan", 1) or 1)
            self.colspan = int(attributes.get("colspan", 1) or 1)
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "table":
            if self.table:
                self.tables.append(self.table)
            self.table = None
        elif tag == "tr" and self.table is not None and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append((" ".join("".join(self.cell).split()), self.rowspan, self.colspan))
            self.cell = None


def _normal(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def _expand(rows):
    expanded, pending = [], {}
    for row in rows:
        output, column, index = [], 0, 0
        while index < len(row):
            if column in pending:
                value, remaining = pending[column]
                output.append(value)
                if remaining == 1:
                    del pending[column]
                else:
                    pending[column] = (value, remaining - 1)
                column += 1
                continue
            value, rowspan, colspan = row[index]
            index += 1
            for offset in range(colspan):
                output.append(value)
                if rowspan > 1:
                    pending[column + offset] = (value, rowspan - 1)
            column += colspan
        expanded.append(output)
    return expanded


def _tables(text):
    parser = TableParser()
    parser.feed(text)
    return [_expand(table) for table in parser.tables]


def _markdown_tables(text):
    tables, current = [], []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def _all_tables(pages):
    result = []
    for page in pages:
        result.extend(_tables(page))
        result.extend(_markdown_tables(page))
    return result


def _plain_text(pages):
    return " ".join(re.sub(r"<[^>]+>", " ", page) for page in pages)


def _number(value):
    match = re.search(r"-?[\d,.]+", str(value or ""))
    if not match:
        return None
    number = match.group(0).replace(",", "")
    return float(number) if "." in number else int(number)


def _date(text):
    matches = re.findall(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})", text)
    if not matches:
        return ""
    year, month, day = matches[-1]
    return f"{year}.{int(month):02d}.{int(day):02d}"


def _criteria(text):
    match = re.search(r"허용\s*기준\s*[:：]?\s*([^<\n]{3,180})", text)
    return match.group(1).strip() if match else ""


def _judgement(text):
    if re.search(r"[☑✓✔]\s*적합|적합\s*[☑✓✔]", text):
        return "적합"
    if re.search(r"[☑✓✔]\s*부적합|부적합\s*[☑✓✔]", text):
        return "부적합"
    return "부적합" if "부적합" in text and "적합" not in text.replace("부적합", "") else "적합"


def _checkbox_value(text):
    text = str(text or "")
    if re.search(r"[☑✓✔]\s*(Yes|있음)|(?:Yes|있음)\s*[☑✓✔]", text, re.I):
        return "Yes"
    if re.search(r"[☑✓✔]\s*(No|없음)|(?:No|없음)\s*[☑✓✔]", text, re.I):
        return "No"
    return "Yes" if "Yes" in text or "있음" in text else "No"


def _measurement_table(table):
    for index, row in enumerate(table):
        normalized = "|".join(_normal(cell) for cell in row)
        if "관리번호" in normalized and "측정위치" in normalized:
            return index, row
    return None, None


def _column(header, keywords):
    for index, cell in enumerate(header):
        normalized = _normal(cell)
        if any(keyword in normalized for keyword in keywords):
            return index
    return None


def _value(row, index):
    return row[index].strip() if index is not None and index < len(row) else ""


def _is_row_number(value):
    return bool(re.fullmatch(r"\s*\d+\s*[.)]?\s*", str(value or "")))


def _deduplicate(records):
    """Keep the first occurrence when OCR repeats a measurement row with spacing changes."""
    unique = []
    seen = set()
    for record in records:
        key = tuple(
            re.sub(r"\s+", "", str(record.get(field, "")))
            for field in ("performed_date", "no", "management_number", "location")
        )
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def _header_and_rows(table):
    header_index, header = _measurement_table(table)
    if header is None:
        return None, []
    data_start = header_index + 1
    while data_start < len(table) and not (table[data_start] and _is_row_number(_value(table[data_start], 0))):
        data_start += 1
    # DeepSeek commonly represents the Particle header across two HTML rows.
    # Joining them preserves labels such as "0.5 μm 이상 부유입자 수/m³".
    header_width = max(len(row) for row in table[header_index:data_start])
    header = [
        " ".join(
            row[column] for row in table[header_index:data_start]
            if column < len(row) and row[column]
        )
        for column in range(header_width)
    ]
    rows = []
    for row in table[data_start:]:
        if row and _is_row_number(_value(row, 0)):
            rows.append(row)
    return header, rows


def _parse_oil_or_moisture(pages, test_type):
    full_text = _plain_text(pages)
    performed_date = _date(full_text)
    criteria = _criteria(full_text)
    judgement = _judgement(full_text)
    records = []
    for table in _all_tables(pages):
        header, rows = _header_and_rows(table)
        if header is None:
            continue
        no_col = _column(header, ["no.", "no"])
        management_col = _column(header, ["관리번호"])
        location_col = _column(header, ["측정위치"])
        result_col = _column(header, ["점검결과"])
        photo_col = _column(header, ["측정사진", "사진첨부"])
        for row in rows:
            result = _value(row, result_col)
            if not result:
                continue
            records.append({
                "no": _value(row, no_col),
                "management_number": _value(row, management_col),
                "location": _value(row, location_col),
                "result_text": result,
                "photo_attached": _checkbox_value(_value(row, photo_col)),
                "judgement": judgement,
                "criteria_text": criteria,
                "performed_date": performed_date,
            })
    return _deduplicate(records)


def _parse_airborne(pages):
    full_text = _plain_text(pages)
    performed_date = _date(full_text)
    criteria = _criteria(full_text)
    judgement = _judgement(full_text)
    records = []
    for table in _all_tables(pages):
        header, rows = _header_and_rows(table)
        if header is None:
            continue
        no_col = _column(header, ["no.", "no"])
        management_col = _column(header, ["관리번호"])
        location_col = _column(header, ["측정위치"])
        grade_col = _column(header, ["grade", "등급"])
        particle_05_col = _column(header, ["0.5μm", "0.5um"])
        particle_50_col = _column(header, ["5.0μm", "5.0um"])
        for row in rows:
            particle_05 = _number(_value(row, particle_05_col))
            particle_50 = _number(_value(row, particle_50_col))
            if particle_05 is None and particle_50 is None:
                continue
            records.append({
                "no": _value(row, no_col),
                "management_number": _value(row, management_col),
                "location": _value(row, location_col),
                "grade": _value(row, grade_col).upper(),
                "particle_05": particle_05 if particle_05 is not None else 0,
                "particle_50": particle_50 if particle_50 is not None else 0,
                "judgement": judgement,
                "criteria_text": criteria,
                "performed_date": performed_date,
            })
    return _deduplicate(records)


def parse_document(test_type, pages, filename=""):
    """Parse all OCR pages from one uploaded PDF into reviewable record rows."""
    if test_type == "oil":
        return _parse_oil_or_moisture(pages, test_type)
    if test_type == "moisture":
        return _parse_oil_or_moisture(pages, test_type)
    if test_type == "airborne":
        return _parse_airborne(pages)
    raise ValueError(f"Unsupported test type: {test_type}")
