import argparse
import csv
import re
from html import unescape
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
HTML_DIR = ROOT_DIR / "data" / "raw" / "distributions"
CSV_DIR = ROOT_DIR / "data" / "generated" / "distributions_csv"
OUTPUT_COLUMNS = [
    "Rank",
    "Division",
    "Players Tracked",
    "Percentile Size",
    "Div I Min",
    "Div I Max",
    "Div II Min",
    "Div II Max",
    "Div III Min",
    "Div III Max",
    "Div IV Min",
    "Div IV Max",
]
DIVISION_LABELS = ["I", "II", "III", "IV"]


def clean_cell(cell_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", cell_html)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text == "-":
        return ""
    if text == "\u2014":
        return ""
    if text == "\u2014 \u2014":
        return ""
    if text == "\u2014" or text == "\u2014 ":
        return ""
    if text == "\u2014".strip():
        return ""
    return "" if text == "\u2014" else text.replace(" \u2014 ", " - ")


def parse_int(value: str) -> int:
    return int(value.replace(",", ""))


def split_rank_and_division(name: str) -> tuple[str, str]:
    match = re.match(r"^(.*)\s+(I|II|III|IV)$", name)
    if not match:
        return name, ""
    return match.group(1), match.group(2)


def parse_range(value: str) -> tuple[str, str]:
    match = re.match(r"^(-?[\d,]+)\s+-\s+([\d,]+)$", value)
    if not match:
        return "", ""
    return str(parse_int(match.group(1))), str(parse_int(match.group(2)))


def normalize_row(row: list[str]) -> dict[str, str]:
    if len(row) != 5:
        raise ValueError(f"Expected 5 columns, got {len(row)}: {row}")

    first_cell = row[0]
    name_match = re.match(r"^(.*?)\s+(\d[\d,]*) players \(([\d.]+)%\)$", first_cell)

    players_tracked = ""
    percentile_size = ""
    rank_name = first_cell
    if name_match:
        rank_name = name_match.group(1)
        players_tracked = str(parse_int(name_match.group(2)))
        percentile_size = name_match.group(3)

    rank, division = split_rank_and_division(rank_name)
    normalized = {
        "Rank": rank,
        "Division": division,
        "Players Tracked": players_tracked,
        "Percentile Size": percentile_size,
        "Div I Min": "",
        "Div I Max": "",
        "Div II Min": "",
        "Div II Max": "",
        "Div III Min": "",
        "Div III Max": "",
        "Div IV Min": "",
        "Div IV Max": "",
    }

    for label, value in zip(DIVISION_LABELS, row[1:]):
        min_value, max_value = parse_range(value)
        normalized[f"Div {label} Min"] = min_value
        normalized[f"Div {label} Max"] = max_value

    return normalized


def parse_table(html_text: str) -> list[list[str]]:
    header_match = re.search(r"<thead[^>]*>(.*?)</thead>", html_text, flags=re.S | re.I)
    body_match = re.search(r"<tbody[^>]*>(.*?)</tbody>", html_text, flags=re.S | re.I)
    if not header_match or not body_match:
        raise ValueError("Expected a table with thead and tbody")

    rows: list[list[str]] = []

    header_cells = re.findall(r"<th[^>]*>(.*?)</th>", header_match.group(1), flags=re.S | re.I)
    if header_cells:
        rows.append([clean_cell(cell) for cell in header_cells])

    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", body_match.group(1), flags=re.S | re.I):
        cell_matches = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.S | re.I)
        if not cell_matches:
            continue
        rows.append([clean_cell(cell) for cell in cell_matches])

    if not rows:
        raise ValueError("No rows parsed from table")

    return rows


def convert_file(html_path: Path, csv_dir: Path) -> Path:
    rows = parse_table(html_path.read_text(encoding="utf-8-sig"))
    normalized_rows = [normalize_row(row) for row in rows[1:]]
    csv_path = csv_dir / f"{html_path.stem}.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(normalized_rows)

    return csv_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert saved Tracker distribution HTML tables to normalized CSV."
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        default=HTML_DIR,
        help="Directory containing raw distribution HTML files.",
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=CSV_DIR,
        help="Directory where generated CSV files should be written.",
    )
    return parser.parse_args()


def repo_relative(path: Path) -> Path:
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def main() -> None:
    args = parse_args()
    html_dir = repo_relative(args.html_dir)
    csv_dir = repo_relative(args.csv_dir)

    html_files = sorted(html_dir.glob("*.html"))
    if not html_files:
        raise SystemExit(f"No HTML files found in {html_dir}/")

    csv_dir.mkdir(parents=True, exist_ok=True)

    for html_path in html_files:
        csv_path = convert_file(html_path, csv_dir)
        print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
