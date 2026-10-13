import os
import csv
from typing import List, Dict, Any
from src.tools.registry import tool_registry


@tool_registry.register("read_csv", "Reads a CSV file into a list of row dictionaries")
def read_csv(file_path: str) -> List[Dict[str, Any]]:
    """Loads a CSV file and returns rows as dictionaries."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found at: {file_path}")

    rows = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k is not None}
            rows.append(clean_row)
    return rows


@tool_registry.register("process_vendor_file", "Ingests, normalizes headers, validates fields, and partitions clean and invalid rows (WF003)")
def process_vendor_file(file_path: str = "data/vendor_raw_feed.csv") -> Dict[str, Any]:
    """
    Executes WF003: Vendor File Processing
    - Detects and normalizes messy column headers
    - Validates required fields: SKU and Product Name (Decision Logic: missing either is invalid)
    - Partitions clean vs invalid rows with detailed error reasons
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Vendor file not found at: {file_path}")

    # Read raw rows
    raw_rows = []
    headers = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx == 0:
                headers = [h.strip() for h in row]
            else:
                if any(cell.strip() for cell in row):
                    raw_rows.append(row)

    # Column normalization mapping
    header_mapping = {}
    normalized_headers = []
    sku_col_idx = None
    name_col_idx = None

    for idx, h in enumerate(headers):
        h_lower = h.lower().replace("_", "").replace(" ", "").replace("-", "")
        if h_lower in ["itemcode", "sku", "itemno", "skucode", "productcode"]:
            header_mapping[h] = "sku"
            sku_col_idx = idx
        elif h_lower in ["producttitle", "productname", "title", "itemname", "description"]:
            header_mapping[h] = "product_name"
            name_col_idx = idx
        elif h_lower in ["categoryname", "category", "cat"]:
            header_mapping[h] = "category"
        elif h_lower in ["costprice", "price", "cost", "unitcost"]:
            header_mapping[h] = "cost_price"
        elif h_lower in ["supplierstock", "stock", "quantity", "qty"]:
            header_mapping[h] = "stock"
        else:
            header_mapping[h] = h.lower()
        normalized_headers.append(header_mapping[h])

    if sku_col_idx is None:
        sku_col_idx = 0  # Default fallback to first column
    if name_col_idx is None:
        name_col_idx = 1  # Default fallback to second column

    cleaned_rows = []
    invalid_rows = []

    for row_num, row in enumerate(raw_rows, start=2):
        row_dict = {}
        for idx, val in enumerate(row):
            col_name = normalized_headers[idx] if idx < len(normalized_headers) else f"col_{idx}"
            row_dict[col_name] = val.strip()

        sku_val = row[sku_col_idx].strip() if sku_col_idx < len(row) else ""
        name_val = row[name_col_idx].strip() if name_col_idx < len(row) else ""

        # Business Rule: Rows missing SKU or product name are invalid
        reasons = []
        if not sku_val:
            reasons.append("Missing mandatory field: SKU")
        if not name_val:
            reasons.append("Missing mandatory field: Product Name")

        if reasons:
            invalid_rows.append({
                "row_number": row_num,
                "data": row_dict,
                "errors": reasons
            })
        else:
            cleaned_rows.append(row_dict)

    return {
        "file_processed": file_path,
        "total_rows_inspected": len(raw_rows),
        "valid_rows_count": len(cleaned_rows),
        "invalid_rows_count": len(invalid_rows),
        "column_normalization_map": header_mapping,
        "cleaned_data_sample": cleaned_rows[:5],
        "all_cleaned_rows": cleaned_rows,
        "invalid_rows_report": invalid_rows
    }
