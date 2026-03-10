from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python scripts/warn_data_js_size.py <old_data_js> <new_data_js>")
        return 2

    old_path = Path(sys.argv[1])
    new_path = Path(sys.argv[2])
    old_size = old_path.stat().st_size
    new_size = new_path.stat().st_size
    if old_size == 0:
        print("Previous data.js size is zero; skipping size anomaly warning.")
        return 0

    change_pct = ((new_size - old_size) / old_size) * 100
    if abs(change_pct) > 20:
        direction = "grew" if change_pct > 0 else "shrank"
        print(f"::warning::data.js {direction} by {abs(change_pct):.1f}% ({old_size} -> {new_size} bytes)")
    else:
        print(f"data.js size change within threshold: {change_pct:.1f}% ({old_size} -> {new_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
