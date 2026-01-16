# app/core/foundry/ingestion/excel_loader.py
from openpyxl import load_workbook

def extract_text_from_xlsx(file_path):
    wb = load_workbook(file_path, data_only=True)
    text = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows(values_only=True):
            row_text = " ".join([str(cell) for cell in row if cell])
            if row_text.strip():
                text.append(row_text)
    return "\n".join(text)

# Example usage
excel_text = extract_text_from_xlsx("app/core/foundry/test_docs/excel_one.xlsx")
print(excel_text)