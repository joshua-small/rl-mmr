# Rocket League MMR Notes

This repo is a small archive of Rocket League MMR/rank data pulled manually
from Tracker Network / tracker.gg, plus a couple of helper scripts that were
used while experimenting with rank distribution parsing.

The main reason this exists: preserve a local, human-readable snapshot of
account ratings, peak ratings, playlist rank cutoffs, player counts, and
percentile sizes so future-me does not have to reverse-engineer what past-me
was doing.

Think of this as a reference snapshot first and a reproducible data pipeline
second. The current YAML is the useful artifact; the exact manual/script split
that produced it is not fully reconstructed.

## Folder Layout

```text
.
|-- config/
|   `-- info.yaml
|-- data/
|   |-- generated/
|   |-- raw/
|   `-- reference/
|       |-- player_info.yaml
|       `-- distributions/
|-- scripts/
|   |-- convert_distributions.py
|   `-- mmr.py
|-- .gitignore
`-- README.md
```

`data/reference/` contains the useful curated YAML snapshot. `data/raw/` is the
place for future saved Tracker HTML captures. `data/generated/` is for derived
outputs like CSVs and is ignored by git except for its placeholder file.

## Data Snapshot

By local file timestamps, the current YAML data was last edited on
April 14, 2026.

The source of truth in this repo is the YAML data:

| File | Purpose |
| --- | --- |
| `config/info.yaml` | Account IDs, playlist IDs, and source URLs used to pull Tracker pages. |
| `data/reference/player_info.yaml` | Manual account snapshots from Tracker profile pages: current playlist MMRs, ranks, divisions, top percentages, match counts, and peak ratings. |
| `data/reference/distributions/*.yaml` | Manual playlist distribution snapshots from Tracker distribution pages. Each file is keyed by playlist ID and includes rank cutoffs, tracked-player counts, and percentile sizes. |
| `scripts/mmr.py` | Legacy parser/calculator for raw Tracker HTML snapshots. It does not currently read the checked-in YAML files. |
| `scripts/convert_distributions.py` | Legacy converter from raw distribution HTML tables to CSV. It expects raw HTML inputs that are not currently checked in. |

Important provenance note: the Tracker HTML was captured manually, and some mix
of manual cleanup plus script output became the YAML data here. The raw HTML
captures are not currently checked in, so the YAML files should be treated as a
trusted local snapshot, not as something this checkout can regenerate from
scratch.

The included playlists are:

| ID | Playlist |
| ---: | --- |
| 10 | Ranked Duel 1v1 |
| 11 | Ranked Doubles 2v2 |
| 13 | Ranked Standard 3v3 |
| 27 | Hoops |
| 28 | Rumble |
| 29 | Dropshot |
| 30 | Snow Day |
| 34 | Tournament Matches |
| 61 | Ranked 4v4 Quads |
| 63 | Heatseeker |

The included account snapshots are:

| Platform | Account |
| --- | --- |
| Epic | `NoNoNo%20GreatPass` |
| Steam | `76561198080314981` |

## External Sources

The data here was pulled manually from Tracker Network:

- Account URLs and distribution URLs are recorded in `config/info.yaml`.
- Distribution files keep each playlist's original Tracker distribution URL in
  the `distribution_url` field.

Some of the same general MMR cutoff information has also been available through
the [RankViewer BakkesMod plugin](https://github.com/BeardedOranges/RankViewer).
RankViewer's own README describes its MMR values as estimates from
[Rocket Tracker](https://rocketleague.tracker.network), so treat it as a useful
reference rather than an official source.

As of April 28, 2026, Rocket League requires Easy Anti-Cheat for online PC play,
and Rocket League says community mods do not run while EAC is enabled:
<https://www.rocketleague.com/en/news/easy-anti-cheat-comes-to-rocket-league-on-pc-today>.
Bakkes also posted that BakkesMod will stop being actively updated and will not
work on Rocket League versions released April 28, 2026 or later:
<https://bakk.es/articles/bakkesmod-eac.html>.

That means RankViewer is still worth acknowledging for provenance and prior art,
but this repo's manually captured Tracker data may be more useful for current
post-EAC snapshots.

## Data Shape

### `data/reference/player_info.yaml`

This file is a list of account snapshots. Each account has:

- `platform`, account identifier, and `profile_url`
- `peak`, including the account's peak rating summary and per-playlist current
  and best MMRs
- `overview`, including current playlist rank, tier, division, MMR, top percent,
  div-up/div-down values, peak rating, and match count

Notes:

- `Casual` appears in account overviews but is intentionally not part of the
  ranked distribution files.
- Tracker sometimes labels Snow Day as `Snowday`; `mmr.py` has an alias for
  this.
- Empty YAML values mean Tracker did not show a value in that field when the
  snapshot was captured.

### `data/reference/distributions/{playlist_id}.yaml`

Each distribution file has:

- `name`
- `id`
- `distribution_url`
- `distribution`

Distribution entries are grouped by rank title. Most ranks contain `Tiers`;
`Supersonic Legend` is a single top-level rank without tiers. When Tracker
shows values for it, those values are stored directly as `min` and `max`.

Tier rows can include:

- `Players Tracked`
- `Percentile Size`
- `Divisions`, a list of division objects with `Division`, `min`, and `max`

Example:

```yaml
distribution:
  - Rank Title: Supersonic Legend
    Players Tracked: 258
    Percentile Size: 0.00
    min: 1355
    max: 1612
  - Rank Title: Grand Champion
    Tiers:
      - Tier: III
        Players Tracked: 496
        Percentile Size: 0.01
        Divisions:
          - Division: I
            min: 1282
            max: 1298
          - Division: II
            min: 1300
            max: 1314
```

Preserve Tracker's gaps between MMR ranges and missing divisions. Those gaps
are not typos; they are how the source page represented division thresholds.

## Scripts

### `scripts/mmr.py`

This script was written for raw HTML snapshots, not the current YAML files.

It expects files like:

```text
accounts/steam/playlists-overview.html
accounts/steam/peak-rating.html
accounts/epic/playlists-overview.html
accounts/epic/peak-rating.html
distributions/{playlist_id}.html
```

By default, those paths live under `data/raw/`:

```text
data/raw/accounts/steam/playlists-overview.html
data/raw/accounts/steam/peak-rating.html
data/raw/accounts/epic/playlists-overview.html
data/raw/accounts/epic/peak-rating.html
data/raw/distributions/{playlist_id}.html
```

When those raw HTML files exist, it:

1. Reads account and playlist config from `config/info.yaml`.
2. Parses current playlist MMRs from profile overview HTML.
3. Parses current and best MMRs from peak-rating HTML.
4. Parses rank distribution buckets from distribution HTML.
5. Interpolates the account's percentile inside the relevant MMR bucket.
6. Prints current ratings and peak-widget playlist comparisons.

In the current checkout, those raw HTML files are absent, so
`python3 scripts/mmr.py` prints headings only.

For a dated raw capture, pass the capture directory explicitly:

```sh
python3 scripts/mmr.py --raw-dir data/raw/2026-04-14
```

### `scripts/convert_distributions.py`

This script expects raw Tracker distribution HTML tables in:

```text
data/raw/distributions/*.html
```

It writes normalized CSVs to:

```text
data/generated/distributions_csv/*.csv
```

The current checkout does not include raw distribution HTML, so
`python3 scripts/convert_distributions.py` exits with:

```text
No HTML files found in <repo>/data/raw/distributions/
```

For a dated raw capture, pass paths explicitly:

```sh
python3 scripts/convert_distributions.py \
  --html-dir data/raw/2026-04-14/distributions \
  --csv-dir data/generated/2026-04-14/distributions_csv
```

## How To Update This Later

1. Open the account and playlist URLs in `config/info.yaml`.
2. Update `data/reference/player_info.yaml` from the Tracker account profile
   pages.
3. Update each `data/reference/distributions/{playlist_id}.yaml` from the
   corresponding Tracker distribution page.
4. Keep playlist IDs and names aligned with `config/info.yaml`.
5. Preserve source values exactly, especially percentile sizes, tracked-player
   counts, and division MMR gaps.
6. Add a capture date somewhere obvious if this becomes more than a one-off
   snapshot.

If the scripts are revived, the most useful next improvement is probably to make
`scripts/mmr.py` consume the YAML distribution files and
`data/reference/player_info.yaml` directly, instead of requiring raw HTML
snapshots.

## Rechecking Accuracy Later

If future-me only wants to know "are these MMR values still roughly right?", do
the smallest useful check first:

1. Pick the playlist in `data/reference/distributions/{playlist_id}.yaml`.
2. Open that file's `distribution_url`.
3. Compare a few rank/division cutoffs around the MMR value you care about.
4. Compare the tracked-player counts and percentile sizes for those nearby
   ranks.
5. If the nearby cutoffs match, the old snapshot is still good enough for that
   question.
6. If they differ, record the new capture date and update only the affected
   playlist/account data.

For a fuller refresh, save the raw Tracker pages before touching YAML. A sane
future layout would be:

```text
data/raw/YYYY-MM-DD/accounts/steam/playlists-overview.html
data/raw/YYYY-MM-DD/accounts/steam/peak-rating.html
data/raw/YYYY-MM-DD/accounts/epic/playlists-overview.html
data/raw/YYYY-MM-DD/accounts/epic/peak-rating.html
data/raw/YYYY-MM-DD/distributions/{playlist_id}.html
```

Then update the YAML from that saved input and leave a note about what was
manual versus scripted. That one habit would make the next archaeology session
dramatically less cursed.

For this repo, "accurate" means "matches Tracker's visible account values and
rank distribution pages at the time of capture." It does not mean official
Psyonix truth, and it does not mean the rank distribution will remain stable
after season resets, playlist population shifts, Tracker changes, or API/page
layout changes.

## Git Ignore Policy

The `.gitignore` ignores Python caches, virtual environments, local editor
state, environment files, and generated outputs under `data/generated/`.

`data/raw/` is intentionally not ignored. Raw Tracker HTML captures are source
evidence for this project, so commit dated captures when they are small enough
and safe to share. If a future capture contains sensitive or huge page data,
store it outside the repo and leave a note in this README.

## Caveats

- Tracker Network data is not official Psyonix data.
- Player counts and percentiles describe tracked players, not necessarily the
  entire Rocket League population.
- Tracker profile "Top %" values and distribution-derived percentiles may differ
  because they can come from different pages, timestamps, or calculation paths.
- RankViewer is a useful historical reference, but it is also based on Tracker
  estimates and should not be treated as a separate official dataset.
