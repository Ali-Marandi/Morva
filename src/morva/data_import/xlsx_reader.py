"""Small dependency-free XLSX table reader for controlled tabular imports.

This reader intentionally supports the subset needed by Morva source reports:
shared strings, inline strings, numeric/text cells, multiple worksheets and
standard A1 references. It does not execute formulas or macros.
"""
from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
CELL_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _column_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - 64)
    return index - 1


def read_xlsx_table(path: str | Path, sheet_name: str | None = None) -> tuple[str, list[str | None], list[dict[str, Any]]]:
    """Read the selected worksheet as header + row dictionaries."""
    xlsx_path = Path(path)
    with zipfile.ZipFile(xlsx_path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", NS):
                shared.append("".join(t.text or "" for t in item.iter("{%s}t" % NS["a"])))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheets = []
        for sheet in workbook.find("a:sheets", NS):
            name = sheet.attrib["name"]
            rid = sheet.attrib["{%s}id" % NS["r"]]
            target = relmap[rid].lstrip("/")
            target = target if target.startswith("xl/") else posixpath.normpath(posixpath.join("xl", target))
            sheets.append((name, target))

        if not sheets:
            raise ValueError(f"No worksheet found in {xlsx_path}")
        selected_name, target = next((x for x in sheets if x[0] == sheet_name), sheets[0]) if sheet_name else sheets[0]
        if sheet_name and selected_name != sheet_name:
            raise ValueError(f"Worksheet {sheet_name!r} not found; available={tuple(name for name, _ in sheets)!r}")

        root = ET.fromstring(archive.read(target))
        raw_rows: list[dict[int, Any]] = []
        max_col = -1
        for row in root.findall(".//a:sheetData/a:row", NS):
            values: dict[int, Any] = {}
            for cell in row.findall("a:c", NS):
                match = CELL_RE.match(cell.attrib["r"])
                if not match:
                    continue
                col_index = _column_index(match.group(1))
                value_node = cell.find("a:v", NS)
                cell_type = cell.attrib.get("t")
                value: Any = None if value_node is None else value_node.text
                if cell_type == "s" and value is not None:
                    value = shared[int(value)]
                elif cell_type == "inlineStr":
                    inline = cell.find("a:is", NS)
                    value = "" if inline is None else "".join(t.text or "" for t in inline.iter("{%s}t" % NS["a"]))
                values[col_index] = value
                max_col = max(max_col, col_index)
            raw_rows.append(values)

        if not raw_rows:
            return selected_name, [], []
        header = [raw_rows[0].get(i) for i in range(max_col + 1)]
        records: list[dict[str, Any]] = []
        for raw in raw_rows[1:]:
            record = {header[i]: raw.get(i) for i in range(max_col + 1) if header[i] not in (None, "") and raw.get(i) is not None}
            if record:
                records.append(record)
        return selected_name, header, records
