"""
Excel ingestion module for RAG pipelines.

Handles .xlsx and .xls file extraction with support for merged cells,
formulas, and multiple sheets. Outputs plain text or markdown tables.
"""
import logging
from io import BytesIO

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.cell.cell import MergedCell
import xlrd

logger = logging.getLogger(__name__)


class ExcelHandler:
    """
    Excel extraction handler for RAG pipelines.

    Accepts bytes and extracts text from .xlsx and .xls files with support for:
    - Multiple sheets
    - Merged cells (value propagation)
    - Formula evaluation (computed values)
    - Markdown table output for structured data

    Attributes:
        output_format: Output format - "text" (plain) or "markdown" (tables).
        include_sheet_names: Include sheet names as headers in output.
        skip_empty_rows: Skip rows that contain no data.
    """

    def __init__(
        self,
        output_format: str = "text",
        include_sheet_names: bool = True,
        skip_empty_rows: bool = True,
    ) -> None:
        """
        Initialize ExcelHandler.

        Args:
            output_format: "text" for plain text, "markdown" for table format.
            include_sheet_names: Whether to include sheet names as headers.
            skip_empty_rows: Whether to skip rows with no data.
        """
        if output_format not in ("text", "markdown"):
            raise ValueError(f"output_format must be 'text' or 'markdown', got: {output_format}")

        self.output_format = output_format
        self.include_sheet_names = include_sheet_names
        self.skip_empty_rows = skip_empty_rows

    def extract(self, data: bytes, extension: str = ".xlsx") -> str:
        """
        Extract text from Excel bytes.

        Args:
            data: Excel file content as bytes.
            extension: File extension to determine format (.xlsx or .xls).

        Returns:
            Extracted text content.

        Raises:
            ValueError: If the file format is not supported.
            RuntimeError: If extraction fails.
        """
        extension = extension.lower()

        if extension == ".xlsx":
            return self._extract_xlsx(data)
        elif extension == ".xls":
            return self._extract_xls(data)
        else:
            raise ValueError(f"Unsupported file format: {extension}. Expected .xlsx or .xls")

    def _extract_xlsx(self, data: bytes) -> str:
        """
        Extract text from .xlsx bytes using openpyxl.

        Args:
            data: XLSX file content as bytes.

        Returns:
            Extracted text content.

        Raises:
            RuntimeError: If extraction fails.
        """
        try:
            # Reason: data_only=True returns computed formula values instead of formulas
            wb = load_workbook(BytesIO(data), data_only=True)
            sheets_output: list[str] = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                sheet_text = self._extract_sheet_xlsx(ws, sheet_name)
                if sheet_text.strip():
                    sheets_output.append(sheet_text)

            wb.close()

            result = "\n\n".join(sheets_output)
            logger.debug(f"Extracted {len(result)} chars from {len(wb.sheetnames)} sheets")
            return result

        except Exception as e:
            logger.error(f"XLSX extraction failed: {e}")
            raise RuntimeError(f"Failed to extract XLSX: {e}") from e

    def _extract_sheet_xlsx(self, ws: Worksheet, sheet_name: str) -> str:
        """
        Extract text from a single xlsx worksheet.

        Args:
            ws: The openpyxl Worksheet object.
            sheet_name: Name of the sheet for headers.

        Returns:
            Extracted text from the sheet.
        """
        merged_values = self._build_merged_cell_map(ws)

        rows_data: list[list[str]] = []
        for row in ws.iter_rows():
            row_values: list[str] = []
            for cell in row:
                value = self._get_cell_value(cell, merged_values)
                row_values.append(value)

            if self.skip_empty_rows and not any(v.strip() for v in row_values):
                continue

            rows_data.append(row_values)

        if not rows_data:
            return ""

        if self.output_format == "markdown":
            return self._format_as_markdown(rows_data, sheet_name)
        else:
            return self._format_as_text(rows_data, sheet_name)

    def _build_merged_cell_map(self, ws: Worksheet) -> dict[str, str]:
        """
        Build a map of merged cell coordinates to their values.

        When cells are merged, only the top-left cell contains the value.
        This map allows retrieving that value for any cell in the merged range.

        Args:
            ws: The openpyxl Worksheet object.

        Returns:
            Dict mapping cell coordinates to merged cell values.
        """
        merged_values: dict[str, str] = {}

        for merged_range in ws.merged_cells.ranges:
            top_left = ws.cell(merged_range.min_row, merged_range.min_col)
            value = str(top_left.value) if top_left.value is not None else ""

            for row in range(merged_range.min_row, merged_range.max_row + 1):
                for col in range(merged_range.min_col, merged_range.max_col + 1):
                    coord = f"{row},{col}"
                    merged_values[coord] = value

        return merged_values

    def _get_cell_value(self, cell, merged_values: dict[str, str]) -> str:
        """
        Get the value of a cell, handling merged cells.

        Args:
            cell: The openpyxl cell object.
            merged_values: Map of merged cell coordinates to values.

        Returns:
            String value of the cell.
        """
        coord = f"{cell.row},{cell.column}"

        if coord in merged_values:
            return merged_values[coord]

        if isinstance(cell, MergedCell):
            return ""

        if cell.value is None:
            return ""
        return str(cell.value)

    def _extract_xls(self, data: bytes) -> str:
        """
        Extract text from legacy .xls bytes using xlrd.

        Args:
            data: XLS file content as bytes.

        Returns:
            Extracted text content.

        Raises:
            RuntimeError: If extraction fails.
        """
        try:
            wb = xlrd.open_workbook(file_contents=data)
            sheets_output: list[str] = []

            for sheet_idx in range(wb.nsheets):
                sheet = wb.sheet_by_index(sheet_idx)
                sheet_text = self._extract_sheet_xls(sheet)
                if sheet_text.strip():
                    sheets_output.append(sheet_text)

            result = "\n\n".join(sheets_output)
            logger.debug(f"Extracted {len(result)} chars from {wb.nsheets} sheets")
            return result

        except Exception as e:
            logger.error(f"XLS extraction failed: {e}")
            raise RuntimeError(f"Failed to extract XLS: {e}") from e

    def _extract_sheet_xls(self, sheet) -> str:
        """
        Extract text from a single xls worksheet.

        Args:
            sheet: The xlrd Sheet object.

        Returns:
            Extracted text from the sheet.
        """
        rows_data: list[list[str]] = []

        for row_idx in range(sheet.nrows):
            row_values: list[str] = []
            for col_idx in range(sheet.ncols):
                cell_value = sheet.cell_value(row_idx, col_idx)
                value = str(cell_value) if cell_value else ""
                row_values.append(value)

            if self.skip_empty_rows and not any(v.strip() for v in row_values):
                continue

            rows_data.append(row_values)

        if not rows_data:
            return ""

        if self.output_format == "markdown":
            return self._format_as_markdown(rows_data, sheet.name)
        else:
            return self._format_as_text(rows_data, sheet.name)

    def _format_as_text(self, rows: list[list[str]], sheet_name: str) -> str:
        """
        Format extracted rows as plain text.

        Args:
            rows: List of row data (each row is a list of cell values).
            sheet_name: Name of the sheet.

        Returns:
            Formatted plain text.
        """
        output: list[str] = []

        if self.include_sheet_names:
            output.append(f"--- Sheet: {sheet_name} ---")

        for row in rows:
            row_text = " | ".join(v for v in row if v.strip())
            if row_text.strip():
                output.append(row_text)

        return "\n".join(output)

    def _format_as_markdown(self, rows: list[list[str]], sheet_name: str) -> str:
        """
        Format extracted rows as a markdown table.

        Args:
            rows: List of row data (each row is a list of cell values).
            sheet_name: Name of the sheet.

        Returns:
            Formatted markdown table.
        """
        if not rows:
            return ""

        output: list[str] = []

        if self.include_sheet_names:
            output.append(f"## {sheet_name}")
            output.append("")

        num_cols = max(len(row) for row in rows)
        normalized_rows = [row + [""] * (num_cols - len(row)) for row in rows]

        header = normalized_rows[0]
        output.append("| " + " | ".join(h if h.strip() else "-" for h in header) + " |")
        output.append("| " + " | ".join("---" for _ in header) + " |")

        for row in normalized_rows[1:]:
            output.append("| " + " | ".join(v if v.strip() else "-" for v in row) + " |")

        return "\n".join(output)
