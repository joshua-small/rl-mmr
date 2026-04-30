import argparse
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config" / "info.yaml"
RAW_DIR = ROOT_DIR / "data" / "raw"
PLAYLIST_ALIASES = {
    "Snowday": "Snow Day",
}


def load_config(config_path=CONFIG_PATH):
    accounts = []
    playlists = []
    current_section = None
    current_item = None

    with config_path.open("r", encoding="utf-8-sig") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped == "accounts:":
                current_section = accounts
                current_item = None
                continue

            if stripped == "playlists:":
                current_section = playlists
                current_item = None
                continue

            if stripped.startswith("- "):
                current_item = {}
                current_section.append(current_item)
                key, value = stripped[2:].split(":", 1)
                current_item[key.strip()] = parse_scalar(value.strip())
                continue

            if current_item is not None and ":" in stripped:
                key, value = stripped.split(":", 1)
                current_item[key.strip()] = parse_scalar(value.strip())

    return {"accounts": accounts, "playlists": playlists}


def parse_scalar(value):
    if value.isdigit():
        return int(value)
    return value


def parse_int(value):
    return int(value.replace(",", ""))


def normalize_playlist(name):
    return PLAYLIST_ALIASES.get(name, name)


def parse_distribution(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = []

    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S):
        name_match = re.search(r'class="[^"]*name[^"]*"[^>]*>([^<]+)</div>', row)
        percent_match = re.search(r"\(([\d.]+)%\)", row)
        if not name_match or not percent_match:
            continue

        mmr_values = []
        for low, high in re.findall("(-?[\\d,]+) \u2014 ([\\d,]+)", row):
            mmr_values.extend([parse_int(low), parse_int(high)])

        if not mmr_values:
            continue

        rows.append(
            {
                "Rank": name_match.group(1).strip(),
                "Percent": float(percent_match.group(1)),
                "MMR Min": min(mmr_values),
                "MMR Max": max(mmr_values),
            }
        )

    if not rows:
        raise ValueError(f"Could not parse distribution rows from {path}")

    rows.sort(key=lambda row: row["MMR Min"])
    return rows


def parse_overview(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    pattern = re.compile(
        r'class="playlist">\s*([^<]+?)\s*(?:<span|<!---->)?</div>'
        r'.*?class="mmr"><div[^>]*class="value">([\d,]+)</div>'
        r'.*?Top ([\d.]+)%',
        flags=re.S,
    )

    rows = []
    for playlist, mmr, top_pct in pattern.findall(text):
        playlist = playlist.strip()
        if playlist == "Casual":
            continue

        rows.append(
            {
                "Playlist": normalize_playlist(playlist),
                "MMR": parse_int(mmr),
                "Profile Top %": float(top_pct),
            }
        )

    return rows


def parse_peak(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    sections = re.split(r"(<h3[^>]*>[^<]+</h3>)", text)
    rows = []

    for idx in range(1, len(sections), 2):
        header = sections[idx]
        body = sections[idx + 1] if idx + 1 < len(sections) else ""

        playlist = re.search(r"<h3[^>]*>([^<]+)</h3>", header).group(1).strip()
        current_block = re.search(
            r'Current</span>.*?<span[^>]*class="value">([\d,]+)</span>(.*?)(?:<h4[^>]*>\s*<span[^>]*>Best</span>)',
            body,
            flags=re.S,
        )
        best_block = re.search(
            r'Best</span>.*?<span[^>]*class="value">([\d,]+)</span>',
            body,
            flags=re.S,
        )

        if not current_block or not best_block:
            continue

        top_match = re.search(r"Top ([\d.]+)%", current_block.group(2))
        rows.append(
            {
                "Playlist": normalize_playlist(playlist),
                "Current MMR": parse_int(current_block.group(1)),
                "Current Profile Top %": float(top_match.group(1)) if top_match else None,
                "Best MMR": parse_int(best_block.group(1)),
            }
        )

    return rows


def percentile_for_mmr(mmr, dist):
    if mmr < dist[0]["MMR Min"]:
        return 0.0

    cumulative = 0.0
    for row in dist:
        low = row["MMR Min"]
        high = row["MMR Max"]
        bucket = row["Percent"]

        if mmr > high:
            cumulative += bucket
            continue

        span = max(high - low, 1)
        position = min(max((mmr - low) / span, 0.0), 1.0)
        return cumulative + bucket * position

    return 100.0


def account_key(account):
    if account.get("steamId"):
        return "steam"
    if account.get("epicProfile"):
        return "epic"
    raise ValueError(f"Unsupported account in {account}")


def compute_percentiles(config, raw_dir=RAW_DIR):
    accounts_dir = raw_dir / "accounts"
    distributions_dir = raw_dir / "distributions"
    distributions = {
        playlist["name"]: parse_distribution(distributions_dir / f"{playlist['playlist']}.html")
        for playlist in config["playlists"]
        if (distributions_dir / f"{playlist['playlist']}.html").exists()
    }

    current_results = []
    peak_results = []

    for account in config["accounts"]:
        key = account_key(account)
        account_name = str(account.get("steamId") or account.get("epicProfile"))

        overview_path = accounts_dir / key / "playlists-overview.html"
        peak_path = accounts_dir / key / "peak-rating.html"

        if overview_path.exists():
            for row in parse_overview(overview_path):
                dist = distributions.get(row["Playlist"])
                if not dist:
                    continue

                percentile = percentile_for_mmr(row["MMR"], dist)
                current_results.append(
                    {
                        "Account": account_name,
                        "Playlist": row["Playlist"],
                        "MMR": row["MMR"],
                        "Percentile": percentile,
                        "Top %": 100.0 - percentile,
                        "Profile Top %": row["Profile Top %"],
                    }
                )

        if peak_path.exists():
            for row in parse_peak(peak_path):
                dist = distributions.get(row["Playlist"])
                if not dist:
                    continue

                current_percentile = percentile_for_mmr(row["Current MMR"], dist)
                best_percentile = percentile_for_mmr(row["Best MMR"], dist)
                peak_results.append(
                    {
                        "Account": account_name,
                        "Playlist": row["Playlist"],
                        "Current MMR": row["Current MMR"],
                        "Current Percentile": current_percentile,
                        "Current Top %": 100.0 - current_percentile,
                        "Best MMR": row["Best MMR"],
                        "Best Percentile": best_percentile,
                        "Best Top %": 100.0 - best_percentile,
                    }
                )

    return current_results, peak_results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse saved Tracker HTML snapshots and estimate MMR percentiles."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Path to the account/playlist config YAML.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory containing accounts/ and distributions/ raw HTML snapshots.",
    )
    return parser.parse_args()


def repo_relative(path):
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def main():
    args = parse_args()
    config = load_config(repo_relative(args.config))
    current_results, peak_results = compute_percentiles(config, repo_relative(args.raw_dir))

    print("Current ratings")
    for row in sorted(current_results, key=lambda item: (item["Account"], item["Playlist"])):
        print(
            f"{row['Account']} | {row['Playlist']}: "
            f"MMR {row['MMR']} | percentile {row['Percentile']:.2f} | top {row['Top %']:.2f}%"
        )

    print("\nPeak widget playlists")
    for row in sorted(peak_results, key=lambda item: (item["Account"], item["Playlist"])):
        print(
            f"{row['Account']} | {row['Playlist']}: "
            f"current {row['Current MMR']} ({row['Current Percentile']:.2f} percentile, top {row['Current Top %']:.2f}%) | "
            f"best {row['Best MMR']} ({row['Best Percentile']:.2f} percentile, top {row['Best Top %']:.2f}%)"
        )


if __name__ == "__main__":
    main()
