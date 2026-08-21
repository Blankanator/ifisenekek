from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "data" / "songs.json"
DATA_JS = ROOT / "data" / "data.js"
REPORT = ROOT / "maintenance-report.txt"


def image_exists(rel_path: str) -> bool:
    return (ROOT / rel_path).is_file()


def expected_page_image(group_id: str, page) -> str:
    return f"sheets/{group_id}/{int(page):03d}.jpg"


def main():
    if not DATA_JSON.exists():
        print("HIBA: data/songs.json nem található.")
        sys.exit(1)

    data = json.loads(DATA_JSON.read_text(encoding="utf-8"))

    removed_segments = []
    removed_pages = []
    unavailable = []
    checked_entries = 0

    for song in data.get("songs", []):
        for group_id, entries in song.get("groups", {}).items():
            for entry in entries:
                checked_entries += 1
                number = entry.get("number", "?")
                label = f"{group_id} {number} – {song.get('title', '')}"

                # 1. Explicit crop/image segments.
                if "sourceSegments" in entry:
                    old_segments = entry.get("sourceSegments") or []
                    good_segments = []

                    for segment in old_segments:
                        rel = segment.get("image", "")
                        if rel and image_exists(rel):
                            good_segments.append(segment)
                        else:
                            removed_segments.append(f"{label}: {rel or '[nincs fájlnév]'}")

                    entry["sourceSegments"] = good_segments

                # 2. Whole-page image lists.
                if "sourcePages" in entry:
                    old_pages = entry.get("sourcePages") or []
                    good_pages = []

                    for page in old_pages:
                        rel = expected_page_image(group_id, page)
                        if image_exists(rel):
                            good_pages.append(page)
                        else:
                            removed_pages.append(f"{label}: {rel}")

                    entry["sourcePages"] = good_pages

                # 3. Determine whether at least one display image remains.
                has_image = False

                if entry.get("sourceSegments"):
                    has_image = True
                elif entry.get("sourcePages"):
                    has_image = True
                else:
                    # Some groups use only sourcePage.
                    source_page = entry.get("sourcePage")
                    if source_page is not None:
                        rel = expected_page_image(group_id, source_page)
                        if image_exists(rel):
                            has_image = True

                if has_image:
                    entry.pop("imageMissing", None)
                else:
                    entry["imageMissing"] = True
                    unavailable.append(label)

    # songs.json stays the editable source of truth.
    DATA_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Rebuild data.js used when index.html is opened directly from Windows.
    DATA_JS.write_text(
        "window.SONG_DB = " +
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) +
        ";\n",
        encoding="utf-8"
    )

    lines = [
        "Ifis énekek – karbantartási jelentés",
        "=" * 42,
        f"Ellenőrzött csoport-ének bejegyzések: {checked_entries}",
        f"Törölt hiányzó crop-hivatkozások: {len(removed_segments)}",
        f"Törölt hiányzó oldal-hivatkozások: {len(removed_pages)}",
        f"Kép nélkül maradt bejegyzések: {len(unavailable)}",
        "",
    ]

    if removed_segments:
        lines += ["TÖRÖLT CROP-HIVATKOZÁSOK", "-" * 28]
        lines += removed_segments
        lines += [""]

    if removed_pages:
        lines += ["TÖRÖLT OLDAL-HIVATKOZÁSOK", "-" * 28]
        lines += removed_pages
        lines += [""]

    if unavailable:
        lines += ["FIGYELEM – KÉP NÉLKÜL MARADT", "-" * 30]
        lines += unavailable
        lines += [""]

    if not (removed_segments or removed_pages or unavailable):
        lines.append("Minden rendben, nem kellett semmit javítani.")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("KÉSZ.")
    print(f"Ellenőrzött bejegyzések: {checked_entries}")
    print(f"Eltávolított crop-hivatkozások: {len(removed_segments)}")
    print(f"Eltávolított oldal-hivatkozások: {len(removed_pages)}")
    print(f"Kép nélkül maradt bejegyzések: {len(unavailable)}")
    print()
    print("Részletes jelentés: maintenance-report.txt")
    print("A data/data.js újragenerálva a data/songs.json alapján.")


if __name__ == "__main__":
    main()
