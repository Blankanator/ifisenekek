
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, shutil, re, unicodedata
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = ROOT / "data" / "songs.json"
DATA_JS = ROOT / "data" / "data.js"
BACKUP_DIR = ROOT / "data" / "backups"


def normalize(text):
    text = unicodedata.normalize("NFD", str(text).lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def slugify(text):
    return normalize(text).replace(" ", "-") or "enek"


class SongModifier(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ifis énekek – mini módosító")
        self.geometry("920x650")
        self.minsize(820, 580)

        self.data = self.load_data()
        self.selected_image = None
        self.current_entry = None

        self.build_ui()
        self.refresh_groups()
        self.refresh_list()

    def load_data(self):
        if not DATA_JSON.exists():
            messagebox.showerror("Hiba", f"Nem található:\n{DATA_JSON}")
            raise SystemExit
        return json.loads(DATA_JSON.read_text(encoding="utf-8"))

    def save_data(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(DATA_JSON, BACKUP_DIR / f"songs_{stamp}.json")

        DATA_JSON.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        DATA_JS.write_text(
            "window.SONG_DB = " +
            json.dumps(self.data, ensure_ascii=False, separators=(",", ":")) +
            ";\n",
            encoding="utf-8"
        )

    def build_ui(self):
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(
            outer,
            text="Ifis énekek – mini módosító",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            outer,
            text="Ének hozzáadása, módosítása vagy törlése. Minden mentés előtt automatikus biztonsági mentés készül."
        )
        subtitle.pack(anchor="w", pady=(2, 14))

        body = ttk.Panedwindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=(0, 0, 12, 0))
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)

        # LEFT: editor
        form = ttk.LabelFrame(left, text="Ének adatai", padding=12)
        form.pack(fill="x")

        ttk.Label(form, text="Csoport").grid(row=0, column=0, sticky="w", pady=5)
        self.group_var = tk.StringVar()
        self.group_cb = ttk.Combobox(form, textvariable=self.group_var, state="readonly", width=28)
        self.group_cb.grid(row=0, column=1, sticky="ew", pady=5)
        self.group_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())

        ttk.Label(form, text="Sorszám").grid(row=1, column=0, sticky="w", pady=5)
        self.number_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.number_var).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(form, text="Cím").grid(row=2, column=0, sticky="w", pady=5)
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var).grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(form, text="Képfájl").grid(row=3, column=0, sticky="nw", pady=5)
        img_row = ttk.Frame(form)
        img_row.grid(row=3, column=1, sticky="ew", pady=5)
        self.image_var = tk.StringVar(value="Nincs kiválasztva")
        ttk.Label(img_row, textvariable=self.image_var, wraplength=280).pack(side="left", fill="x", expand=True)
        ttk.Button(img_row, text="Tallózás…", command=self.choose_image).pack(side="right", padx=(8,0))

        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=12)

        ttk.Button(btns, text="＋ Hozzáadás", command=self.add_song).pack(fill="x", pady=4)
        ttk.Button(btns, text="✎ Módosítás mentése", command=self.modify_song).pack(fill="x", pady=4)
        ttk.Button(btns, text="⇄ Összevonás", command=self.merge_song).pack(fill="x", pady=4)
        ttk.Button(btns, text="🗑 Törlés", command=self.delete_song).pack(fill="x", pady=4)

        helpbox = ttk.LabelFrame(left, text="Használat", padding=10)
        helpbox.pack(fill="x", pady=(8,0))
        ttk.Label(
            helpbox,
            wraplength=330,
            justify="left",
            text=(
                "Hozzáadás: válassz csoportot, adj meg sorszámot, címet és képet.\n\n"
                "Módosítás: kattints egy énekre a jobb oldali listában, változtasd meg, amit szeretnél, majd mentsd.\n\n"
                "Összevonás: válassz ki egy éneket, majd válaszd ki, melyik másik énekbe kerüljön. A cél ének címe marad meg, az összes csoportváltozat egyesül.\n\n"
                "Törlés: válassz ki egy éneket, majd töröld. Csak az adott csoport változata törlődik."
            )
        ).pack(anchor="w")

        # RIGHT: list
        top = ttk.Frame(right)
        top.pack(fill="x")

        ttk.Label(top, text="Keresés").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(8,0))
        self.search_var.trace_add("write", lambda *_: self.refresh_list())

        list_frame = ttk.Frame(right)
        list_frame.pack(fill="both", expand=True, pady=(10,0))

        self.tree = ttk.Treeview(
            list_frame,
            columns=("number", "title"),
            show="headings",
            selectmode="browse"
        )
        self.tree.heading("number", text="Sorszám")
        self.tree.heading("title", text="Cím")
        self.tree.column("number", width=90, anchor="center")
        self.tree.column("title", width=430)
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self.load_selected)

        self.status_var = tk.StringVar(value="Kész.")
        ttk.Label(outer, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", pady=(12,0))

    def refresh_groups(self):
        groups = sorted(
            self.data.get("groups", {}).items(),
            key=lambda kv: kv[1]["name"].casefold()
        )
        self.group_name_to_id = {info["name"]: gid for gid, info in groups}
        names = list(self.group_name_to_id)
        self.group_cb["values"] = names
        if names and not self.group_var.get():
            self.group_var.set(names[0])

    def current_group_id(self):
        return self.group_name_to_id.get(self.group_var.get())

    def iter_group_entries(self, gid):
        for song in self.data.get("songs", []):
            for idx, entry in enumerate(song.get("groups", {}).get(gid, [])):
                yield song, idx, entry

    def refresh_list(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        gid = self.current_group_id()
        if not gid:
            return

        q = normalize(self.search_var.get())
        rows = []
        for song, idx, entry in self.iter_group_entries(gid):
            if q and q not in normalize(song["title"]) and q not in str(entry.get("number", "")):
                continue
            rows.append((song, idx, entry))

        def sort_key(row):
            num = row[2].get("number", "")
            try:
                return (0, int(num))
            except:
                return (1, str(num))

        rows.sort(key=sort_key)

        for song, idx, entry in rows:
            iid = f"{song['id']}::{idx}"
            self.tree.insert("", "end", iid=iid, values=(entry.get("number",""), song["title"]))

        self.status_var.set(f"{len(rows)} ének a kiválasztott csoportban.")

    def load_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        song_id, idx = iid.rsplit("::", 1)
        idx = int(idx)
        gid = self.current_group_id()

        song = next((s for s in self.data["songs"] if s["id"] == song_id), None)
        if not song:
            return

        entry = song["groups"][gid][idx]
        self.current_entry = (song, gid, idx, entry)

        self.number_var.set(str(entry.get("number","")))
        self.title_var.set(song["title"])
        self.selected_image = None

        segs = entry.get("sourceSegments") or []
        if segs and segs[0].get("image"):
            self.image_var.set(segs[0]["image"])
        else:
            self.image_var.set("Nincs kiválasztva")

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Képfájl kiválasztása",
            filetypes=[
                ("Képek", "*.jpg *.jpeg *.png *.webp"),
                ("Minden fájl", "*.*")
            ]
        )
        if path:
            self.selected_image = Path(path)
            self.image_var.set(str(self.selected_image))

    def validate_form(self, require_image=False):
        gid = self.current_group_id()
        if not gid:
            messagebox.showwarning("Hiányzó adat", "Válassz csoportot.")
            return None

        number = self.number_var.get().strip()
        title = self.title_var.get().strip()

        if not number:
            messagebox.showwarning("Hiányzó adat", "Add meg a sorszámot.")
            return None
        if not title:
            messagebox.showwarning("Hiányzó adat", "Add meg a címet.")
            return None
        if require_image and not self.selected_image:
            messagebox.showwarning("Hiányzó adat", "Válassz képfájlt.")
            return None

        return gid, number, title

    def find_song_by_title(self, title):
        key = normalize(title)
        for song in self.data["songs"]:
            if normalize(song["title"]) == key:
                return song
            if any(normalize(a) == key for a in song.get("aliases", [])):
                return song
        return None

    def make_song_id(self, title):
        base = slugify(title)
        used = {s["id"] for s in self.data["songs"]}
        sid = base
        i = 2
        while sid in used:
            sid = f"{base}-{i}"
            i += 1
        return sid

    def copy_image(self, gid, number, source):
        ext = source.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg"

        dest_dir = ROOT / "sheets" / gid / "manual"
        dest_dir.mkdir(parents=True, exist_ok=True)

        safe_number = re.sub(r"[^0-9A-Za-z_-]+", "_", str(number))
        dest = dest_dir / f"{safe_number}{ext}"
        shutil.copy2(source, dest)
        return dest.relative_to(ROOT).as_posix()

    def add_song(self):
        values = self.validate_form(require_image=True)
        if not values:
            return
        gid, number, title = values

        # Prevent same group/number being added twice.
        for song, idx, entry in self.iter_group_entries(gid):
            if str(entry.get("number")) == str(number):
                messagebox.showerror(
                    "Már létezik",
                    f"Ebben a csoportban már van {number} sorszámú ének:\n{song['title']}"
                )
                return

        song = self.find_song_by_title(title)
        if song is None:
            song = {
                "id": self.make_song_id(title),
                "title": title,
                "searchTitle": normalize(title),
                "groups": {}
            }
            self.data["songs"].append(song)

        rel = self.copy_image(gid, number, self.selected_image)
        song.setdefault("groups", {}).setdefault(gid, []).append({
            "number": int(number) if number.isdigit() else number,
            "section": self.data["groups"][gid]["name"],
            "sourceSegments": [{"image": rel}]
        })

        self.save_data()
        self.selected_image = None
        self.image_var.set("Nincs kiválasztva")
        self.refresh_list()
        self.status_var.set(f"Hozzáadva: {number} – {title}")
        messagebox.showinfo("Kész", "Az ének hozzáadva.")

    def modify_song(self):
        if not self.current_entry:
            messagebox.showwarning("Nincs kijelölés", "Előbb válassz ki egy éneket a jobb oldali listából.")
            return

        values = self.validate_form(require_image=False)
        if not values:
            return
        new_gid, new_number, new_title = values

        song, old_gid, idx, entry = self.current_entry

        # Collision check, ignoring the currently edited entry.
        for other_song, other_idx, other_entry in self.iter_group_entries(new_gid):
            if other_song is song and new_gid == old_gid and other_idx == idx:
                continue
            if str(other_entry.get("number")) == str(new_number):
                messagebox.showerror(
                    "Sorszám ütközés",
                    f"A {new_number} sorszám már foglalt ebben a csoportban."
                )
                return

        # If group changed, move the entry.
        if new_gid != old_gid:
            song["groups"][old_gid].pop(idx)
            if not song["groups"][old_gid]:
                del song["groups"][old_gid]
            song.setdefault("groups", {}).setdefault(new_gid, []).append(entry)

        song["title"] = new_title
        song["searchTitle"] = normalize(new_title)
        entry["number"] = int(new_number) if new_number.isdigit() else new_number
        entry["section"] = self.data["groups"][new_gid]["name"]

        if self.selected_image:
            # Delete old explicit images for this entry.
            for seg in entry.get("sourceSegments", []) or []:
                rel = seg.get("image")
                if rel:
                    old_file = ROOT / rel
                    if old_file.exists():
                        try:
                            old_file.unlink()
                        except:
                            pass
            rel = self.copy_image(new_gid, new_number, self.selected_image)
            entry["sourceSegments"] = [{"image": rel}]
            entry.pop("sourcePages", None)
            entry.pop("sourcePage", None)

        self.save_data()
        self.current_entry = None
        self.selected_image = None
        self.image_var.set("Nincs kiválasztva")
        self.refresh_groups()
        self.refresh_list()
        self.status_var.set(f"Módosítva: {new_number} – {new_title}")
        messagebox.showinfo("Kész", "A módosítások mentve.")

    def merge_song(self):
        if not self.current_entry:
            messagebox.showwarning(
                "Nincs kijelölés",
                "Előbb válaszd ki azt az éneket a jobb oldali listából, amelyet egy másik énekbe szeretnél összevonni."
            )
            return

        source_song = self.current_entry[0]
        candidates = sorted(
            [s for s in self.data["songs"] if s is not source_song],
            key=lambda s: s["title"].casefold()
        )
        if not candidates:
            messagebox.showwarning("Nincs cél", "Nincs másik ének, amellyel össze lehetne vonni.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Énekek összevonása")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Ezt az éneket vonjuk össze:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Label(frame, text=source_song["title"], wraplength=480).pack(anchor="w", pady=(2, 12))
        ttk.Label(frame, text="Cél ének (ennek a címe marad meg):", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        target_var = tk.StringVar()
        titles = [s["title"] for s in candidates]
        combo = ttk.Combobox(frame, textvariable=target_var, values=titles, width=62)
        combo.pack(fill="x", pady=(4, 8))
        combo.focus_set()

        hint = ttk.Label(
            frame,
            text="Kezdj el gépelni a cím kereséséhez. Az összevonás után a forrás ének külön bejegyzése megszűnik, de a csoportváltozatai megmaradnak a cél ének alatt.",
            wraplength=500,
            justify="left"
        )
        hint.pack(anchor="w", pady=(0, 12))

        def filter_targets(_event=None):
            q = normalize(target_var.get())
            if not q:
                combo["values"] = titles
            else:
                combo["values"] = [s["title"] for s in candidates if q in normalize(s["title"])]

        combo.bind("<KeyRelease>", filter_targets)

        def do_merge():
            wanted = target_var.get().strip()
            target_song = next((s for s in candidates if s["title"] == wanted), None)
            if target_song is None:
                # Also allow an exact normalized title typed manually.
                key = normalize(wanted)
                target_song = next((s for s in candidates if normalize(s["title"]) == key), None)
            if target_song is None:
                messagebox.showwarning("Válassz cél éneket", "Válassz egy létező éneket a listából.", parent=dialog)
                return

            if not messagebox.askyesno(
                "Összevonás megerősítése",
                f"Összevonod ezt:\n\n{source_song['title']}\n\nebbe:\n\n{target_song['title']}\n\nA megmaradó cím: {target_song['title']}",
                parent=dialog
            ):
                return

            # Preserve the old source title as an alias, so search still finds it.
            aliases = set(target_song.get("aliases", []))
            aliases.update(source_song.get("aliases", []))
            if normalize(source_song["title"]) != normalize(target_song["title"]):
                aliases.add(source_song["title"])
            aliases.discard(target_song["title"])
            if aliases:
                target_song["aliases"] = sorted(aliases, key=str.casefold)

            # Move every group/version from source to target.
            for gid, entries in source_song.get("groups", {}).items():
                dest = target_song.setdefault("groups", {}).setdefault(gid, [])
                for entry in entries:
                    if entry not in dest:
                        dest.append(entry)

            self.data["songs"].remove(source_song)
            target_song["searchTitle"] = normalize(target_song["title"])
            self.save_data()

            self.current_entry = None
            self.number_var.set("")
            self.title_var.set("")
            self.selected_image = None
            self.image_var.set("Nincs kiválasztva")
            self.refresh_list()
            self.status_var.set(f"Összevonva: {source_song['title']} → {target_song['title']}")
            dialog.destroy()
            messagebox.showinfo("Kész", f"Az énekek összevonva.\n\nMegmaradó cím: {target_song['title']}")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Mégse", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Összevonás", command=do_merge).pack(side="right", padx=(0, 8))

        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def delete_song(self):
        if not self.current_entry:
            messagebox.showwarning("Nincs kijelölés", "Előbb válassz ki egy éneket a jobb oldali listából.")
            return

        song, gid, idx, entry = self.current_entry
        number = entry.get("number", "")
        title = song["title"]

        if not messagebox.askyesno(
            "Törlés megerősítése",
            f"Törlöd ezt a csoportváltozatot?\n\n{number} – {title}\n\n"
            "A többi csoportban lévő változat megmarad."
        ):
            return

        # Delete explicit image files referenced only by this entry.
        for seg in entry.get("sourceSegments", []) or []:
            rel = seg.get("image")
            if rel:
                file_path = ROOT / rel
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except:
                        pass

        song["groups"][gid].pop(idx)
        if not song["groups"][gid]:
            del song["groups"][gid]

        # Remove catalogue record if it has no group versions left.
        if not song["groups"]:
            self.data["songs"].remove(song)

        self.save_data()
        self.current_entry = None
        self.number_var.set("")
        self.title_var.set("")
        self.selected_image = None
        self.image_var.set("Nincs kiválasztva")
        self.refresh_list()
        self.status_var.set(f"Törölve: {number} – {title}")
        messagebox.showinfo("Kész", "A csoportváltozat törölve.")


if __name__ == "__main__":
    app = SongModifier()
    app.mainloop()
