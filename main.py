"""
PBInfo Tracker — GUI refactoring.
Requires:  pip install customtkinter selenium
"""

import csv
import glob
import threading
import webbrowser
from collections import defaultdict
from datetime import datetime
from tkinter import ttk
import tkinter as tk

import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ══════════════════════════════════════════════════════════════════════
#  BACKEND
# ══════════════════════════════════════════════════════════════════════

class Backend:
    USERNAMES: list[str] = [
        "CiusteaIoana",       "HyKXd",              "Bejan_Olivia",
        "Blaj_Ema",           "marcomihoc",          "Cristian_Ghiorghita",
        "pascal_andrei",      "Mirze_Bianca_Ioana",  "cosmin_ma",
        "carmen_talmaciu",    "erikadobos",          "Andrew_Waltz",
        "Petrisor_Simina",    "MirunaBejenescu",     "Darius_George22",
        "andreea_caliman",    "catiii",              "Fabrizio123",
        "ZahariaAnaEliza",    "malinarobu",          "ButnariuMihaiBogdan",
        "rares_anthony",      "ciobanu_madalina22",  "Matei_Gutu",
    ]

    @staticmethod
    def format_problem_name(name: str) -> str:
        if not name:
            return ""
        return name.replace("-", " ").replace("_", " ").lower().strip()

    @staticmethod
    def get_driver(headless: bool = True) -> webdriver.Chrome:
        opts = webdriver.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-software-rasterizer")
            opts.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(30)
        return driver

    @staticmethod
    def click_initial_button(driver) -> None:
        try:
            xpath = "/html/body/div[3]/div[2]/div[2]/div[2]/div[2]/button[1]"
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            btn.click()
        except Exception:
            pass

    def _scrape_page(self, driver, username: str, log):
        _CSS_BADGES  = "a.badge.bg-secondary.text-decoration-none"
        _CSS_PRIVATE = "h1.text-center.text-danger"
        try:
            WebDriverWait(driver, 7).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, _CSS_BADGES) or
                          d.find_elements(By.CSS_SELECTOR, _CSS_PRIVATE)
            )
            if driver.find_elements(By.CSS_SELECTOR, _CSS_PRIVATE):
                log(f"  -> Profilul lui {username} este privat. Se sare...")
                return [], [], [], []
        except Exception:
            log(f"  -> Timeout / 0 probleme gasite pentru {username}")
            return [], [], [], []

        buttons = driver.find_elements(By.CSS_SELECTOR, _CSS_BADGES)
        solved_i, solved_l, failed_i, failed_l = [], [], [], []
        for btn in buttons:
            raw_style = (btn.get_attribute("style") or "").replace(" ", "").lower()
            is_failed = "color:red" in raw_style
            text = self.format_problem_name(btn.text)
            link = btn.get_attribute("href") or ""
            if link:
                link = link.replace(f"solutii/user/{username}/problema/", "probleme/")
            if not text and link:
                text = self.format_problem_name(link.split("/")[-1])
            if is_failed:
                failed_i.append(text); failed_l.append(link)
            else:
                solved_i.append(text); solved_l.append(link)

        log(f"  -> {len(solved_i)} rezolvate, {len(failed_i)} incercari pentru {username}")
        return solved_i, solved_l, failed_i, failed_l

    def _write_user_csvs(self, username, solved_i, solved_l, failed_i, failed_l) -> None:
        for suffix, items, links in [
            ("",           solved_i, solved_l),
            ("_incercari", failed_i, failed_l),
        ]:
            with open(f"{username}{suffix}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Problema", "Link"])
                w.writerows(zip(items, links))

    def _get_problem_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        try:
            with open("ProblemeAll.csv", encoding="utf-8") as f:
                r = csv.reader(f); next(r)
                for row in r:
                    if len(row) >= 3:
                        try:
                            counts[row[0]] = int(row[2])
                        except (ValueError, IndexError):
                            pass
        except FileNotFoundError:
            pass
        return counts

    def load_user_profile(self, username: str) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for suffix, status in [("", "rezolvata"), ("_incercari", "incercare")]:
            try:
                with open(f"{username}{suffix}.csv", encoding="utf-8") as f:
                    r = csv.reader(f); next(r)
                    for row in r:
                        if len(row) >= 2:
                            rows.append((row[0], row[1], status))
            except FileNotFoundError:
                pass
        return rows

    def load_csv_file(self, filepath: str) -> tuple[list[str], list[list[str]]]:
        try:
            with open(filepath, encoding="utf-8") as f:
                r = csv.reader(f)
                headers = next(r)
                rows = [row for row in r if row]
            return headers, rows
        except (FileNotFoundError, StopIteration):
            return [], []

    def load_probleme_all(self) -> list[list]:
        rows = []
        try:
            with open("ProblemeAll.csv", encoding="utf-8") as f:
                r = csv.reader(f); next(r)
                for row in r:
                    if len(row) >= 3:
                        try:
                            rows.append([row[0], row[1], int(row[2])])
                        except (ValueError, IndexError):
                            rows.append([row[0], row[1], 0])
        except FileNotFoundError:
            pass
        rows.sort(key=lambda x: x[2], reverse=True)
        return rows

    def list_csv_files(self) -> list[str]:
        files = glob.glob("*.csv")
        user_csvs  = sorted(f for f in files if any(f.startswith(u) for u in self.USERNAMES))
        other_csvs = sorted(f for f in files if f not in user_csvs)
        return user_csvs + other_csvs

    # ── Scraping ──────────────────────────────────────────────────────

    def update_all(self, log, progress, headless: bool = True) -> None:
        driver = self.get_driver(headless)
        total = len(self.USERNAMES)
        for i, username in enumerate(self.USERNAMES):
            log(f"[{i+1}/{total}] Scraping: {username}")
            try:
                driver.get(f"https://www.pbinfo.ro/profil/{username}/probleme")
            except Exception:
                try:
                    driver.execute_script("window.stop();")
                except Exception:
                    pass
                log(f"⚠ Timeout pagina {username}, se sare...")
                progress((i + 1) / total)
                continue
            if i == 0:
                self.click_initial_button(driver)
            s_i, s_l, f_i, f_l = self._scrape_page(driver, username, log)
            self._write_user_csvs(username, s_i, s_l, f_i, f_l)
            progress((i + 1) / total)
        driver.quit()
        log("✔ Toate fisierele CSV au fost actualizate.")
        # Auto-rebuild ProblemeAll
        self.update_probleme_all(log)

    def update_single(self, index: int, log, headless: bool = True) -> None:
        if not (0 <= index < len(self.USERNAMES)):
            log("❌ Indice invalid.")
            return
        username = self.USERNAMES[index]
        driver = self.get_driver(headless)
        try:
            driver.get(f"https://www.pbinfo.ro/profil/{username}/probleme")
        except Exception:
            try:
                driver.execute_script("window.stop();")
            except Exception:
                pass
            log(f"❌ Timeout la incarcarea paginii pentru {username}.")
            driver.quit()
            return
        self.click_initial_button(driver)
        log(f"Scraping: {username} ...")
        s_i, s_l, f_i, f_l = self._scrape_page(driver, username, log)
        self._write_user_csvs(username, s_i, s_l, f_i, f_l)
        driver.quit()
        log(f"✔ Problemele pentru {username} au fost actualizate.")
        # Auto-rebuild ProblemeAll
        self.update_probleme_all(log)

    def update_probleme_all(self, log) -> None:
        count: dict[str, int] = defaultdict(int)
        links_map: dict[str, str] = {}
        missing = 0
        for username in self.USERNAMES:
            try:
                with open(f"{username}.csv", encoding="utf-8") as f:
                    r = csv.reader(f); next(r)
                    for row in r:
                        if len(row) >= 2:
                            count[row[0]] += 1
                            links_map[row[0]] = row[1]
            except FileNotFoundError:
                missing += 1
        if missing:
            log(f"⚠ {missing} fisiere CSV lipsa — ignorate.")
        with open("ProblemeAll.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Problema", "Link", "Numar de rezolvari"])
            for p, c in sorted(count.items(), key=lambda x: x[1], reverse=True):
                w.writerow([p, links_map[p], c])
        log(f"✔ ProblemeAll.csv actualizat — {len(count)} probleme distincte.")

    # ── Analiza ───────────────────────────────────────────────────────

    def compare_users(self, i1: int, i2: int, log, direction: str = "u1_not_u2") -> list[list]:
        if direction == "u2_not_u1":
            i1, i2 = i2, i1
        u1, u2 = self.USERNAMES[i1], self.USERNAMES[i2]
        counts = self._get_problem_counts()
        try:
            u1_data: dict[str, str] = {}
            with open(f"{u1}.csv", encoding="utf-8") as f:
                r = csv.reader(f); next(r)
                for row in r:
                    if len(row) >= 2:
                        u1_data[row[0]] = row[1]
            u2_problems: set[str] = set()
            with open(f"{u2}.csv", encoding="utf-8") as f:
                r = csv.reader(f); next(r)
                for row in r:
                    if len(row) >= 1:
                        u2_problems.add(row[0])
        except FileNotFoundError:
            log("❌ Lipsesc fisierele CSV. Actualizeaza datele mai intai.")
            return []

        if direction == "both":
            result = [[p, l, counts.get(p, 0)] for p, l in u1_data.items() if p in u2_problems]
            desc = f"rezolvate de ambii ({u1} si {u2})"
        else:
            result = [[p, l, counts.get(p, 0)] for p, l in u1_data.items() if p not in u2_problems]
            desc = f"rezolvate de {u1}, nerezolvate de {u2}"

        result.sort(key=lambda x: x[2], reverse=True)
        log(f"✔ {len(result)} probleme {desc}")
        return result

    def unresolved_by_user(self, index: int, log) -> list[list]:
        if not (0 <= index < len(self.USERNAMES)):
            return []
        username = self.USERNAMES[index]
        user_problems: set[str] = set()
        try:
            with open(f"{username}.csv", encoding="utf-8") as f:
                r = csv.reader(f); next(r)
                for row in r:
                    user_problems.add(row[0])
        except FileNotFoundError:
            log(f"❌ Fisierul lui {username} nu exista. Actualizeaza datele mai intai.")
            return []
        unresolved: list[list] = []
        try:
            with open("ProblemeAll.csv", encoding="utf-8") as f:
                r = csv.reader(f); next(r)
                for row in r:
                    if len(row) >= 3 and row[0] not in user_problems:
                        try:
                            unresolved.append([row[0], row[1], int(row[2])])
                        except (ValueError, IndexError):
                            unresolved.append([row[0], row[1], 0])
        except FileNotFoundError:
            log("❌ ProblemeAll.csv nu exista. Apasa 'Actualizeaza ProblemeAll' mai intai.")
            return []
        unresolved.sort(key=lambda x: x[2], reverse=True)
        log(f"✔ {len(unresolved)} probleme nerezolvate de {username} — sortate dupa popularitate")
        return unresolved

    def export_results(self, data: list, headers: list[str], filename: str, log) -> None:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(data)
        log(f"✔ Exportat {len(data)} randuri -> {filename}")

    def resolve_username(self, raw: str) -> int:
        raw = raw.strip()
        if raw in self.USERNAMES:
            return self.USERNAMES.index(raw)
        lower = raw.lower()
        for i, u in enumerate(self.USERNAMES):
            if u.lower() == lower:
                return i
        return -1


# ══════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════

_LOG_COLORS = {
    "ok":   "#4ade80",
    "err":  "#f87171",
    "warn": "#fbbf24",
    "info": "#94a3b8",
    "ts":   "#475569",
}

_TV = {
    "bg":        "#1e1e2e",
    "bg_alt":    "#181825",
    "bg_head":   "#11111b",
    "fg":        "#cdd6f4",
    "fg_head":   "#89b4fa",
    "sel_bg":    "#313244",
    "sel_fg":    "#cdd6f4",
    "solved_bg": "#1a2b1a",
    "solved_fg": "#a6e3a1",
    "inc_bg":    "#2d1b1b",
    "inc_fg":    "#f38ba8",
    "diff5_bg":  "#1a3020",
    "diff5_fg":  "#a6e3a1",
    "diff4_bg":  "#162820",
    "diff4_fg":  "#94e2c8",
    "diff3_bg":  "#2a2510",
    "diff3_fg":  "#f9e2af",
    "diff2_bg":  "#2a1c10",
    "diff2_fg":  "#fab387",
    "diff1_bg":  "#2d1b1b",
    "diff1_fg":  "#f38ba8",
    "pop_bg":    "#1a2520",
    "pop_fg":    "#94e2c8",
    "rare_bg":   "#2a2010",
    "rare_fg":   "#f9e2af",
    "font":      ("Consolas", 11),
    "head_font": ("Consolas", 11, "bold"),
    "row_h":     26,
}


# ══════════════════════════════════════════════════════════════════════
#  SEARCHABLE USER COMBOBOX
# ══════════════════════════════════════════════════════════════════════

class UserComboBox(ctk.CTkFrame):
    """
    Entry + dropdown cu filtrare live, case-insensitive.
    • Click pe entry → sterge textul curent si deschide dropdown cu toate optiunile
    • Tastare → filtreaza in timp real (ignore uppercase/lowercase)
    • ↑ / ↓ → naviga in lista; Enter → selecteaza; Escape → inchide
    • Click pe item → selecteaza si inchide
    • Scrollbar daca lista e lunga
    """

    def __init__(self, master, values: list[str], variable: ctk.StringVar,
                 width: int = 220, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._all_values  = values
        self._var         = variable
        self._on_change   = on_change
        self._dropdown    = None
        self._listbox     = None
        self._skip_trace  = False   # evita re-intrare in trace la set programatic
        self._bind_global = None    # global click-outside handler funcid

        self._entry = ctk.CTkEntry(
            self, textvariable=self._var,
            width=width - 38, height=34, corner_radius=8,
            placeholder_text="Scrie sau alege...",
        )
        self._entry.pack(side="left")

        self._btn = ctk.CTkButton(
            self, text="▾", width=34, height=34, corner_radius=8,
            fg_color=("#1e1e2e", "#1e1e2e"),
            hover_color=("#313244", "#313244"),
            text_color="#89b4fa",
            font=ctk.CTkFont(size=14),
            command=self._toggle_dropdown,
        )
        self._btn.pack(side="left", padx=(2, 0))

        # Cand utilizatorul da click pe entry: sterge si deschide
        self._entry._entry.bind("<FocusIn>",  self._on_entry_click)
        self._entry._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry._entry.bind("<Down>",      lambda e: (self._ensure_open(), self._move_sel(1)))
        self._entry._entry.bind("<Up>",        lambda e: (self._ensure_open(), self._move_sel(-1)))
        self._entry._entry.bind("<Return>",    self._on_enter)
        self._entry._entry.bind("<Escape>",    lambda e: self._close_dropdown())

        self._var.trace_add("write", self._on_trace)

    # ── Handlers entry ───────────────────────────────────────────────

    def _on_entry_click(self, _event):
        """Sterge textul existent si deschide dropdown cu toate optiunile."""
        if not self._skip_trace:
            self._skip_trace = True
            self._var.set("")
            self._skip_trace = False
        self._open_dropdown()

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        self._refresh_dropdown()

    def _on_trace(self, *_):
        if self._skip_trace:
            return
        if self._on_change:
            self._on_change(self._var.get())

    def _on_enter(self, _event):
        """Selecteaza primul item din lista sau itemul curent selectat."""
        if self._listbox and self._dropdown and self._dropdown.winfo_exists():
            sel = self._listbox.curselection()
            if sel:
                self._select_item(self._listbox.get(sel[0]).strip())
                return
            if self._listbox.size() > 0:
                self._select_item(self._listbox.get(0).strip())
        self._close_dropdown()

    # ── Navigare cu sageti ───────────────────────────────────────────

    def _ensure_open(self):
        if not (self._dropdown and self._dropdown.winfo_exists()):
            self._open_dropdown()

    def _move_sel(self, delta: int):
        if not (self._listbox and self._dropdown and self._dropdown.winfo_exists()):
            return
        n = self._listbox.size()
        if n == 0:
            return
        cur = self._listbox.curselection()
        if cur:
            idx = max(0, min(n - 1, cur[0] + delta))
        else:
            idx = 0 if delta > 0 else n - 1
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(idx)
        self._listbox.see(idx)

    # ── Dropdown open / close / refresh ─────────────────────────────

    def _toggle_dropdown(self):
        if self._dropdown and self._dropdown.winfo_exists():
            self._close_dropdown()
        else:
            # La click pe buton: sterge textul pentru a arata toate optiunile
            self._skip_trace = True
            self._var.set("")
            self._skip_trace = False
            self._open_dropdown()

    def _filtered(self) -> list[str]:
        q = self._var.get().strip().lower()
        return [v for v in self._all_values if q in v.lower()] if q else list(self._all_values)

    def _open_dropdown(self):
        self._close_dropdown()
        filtered = self._filtered()
        if not filtered:
            return

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        w = self.winfo_width()
        rows = min(len(filtered), 10)
        row_h = 28
        h = rows * row_h + 8

        self._dropdown = tk.Toplevel(self)
        self._dropdown.wm_overrideredirect(True)
        self._dropdown.wm_geometry(f"{w}x{h}+{x}+{y}")
        self._dropdown.configure(bg=_TV["bg_head"])
        self._dropdown.attributes("-topmost", True)

        # Scrollbar daca sunt mai mult de 10 iteme
        frame = tk.Frame(self._dropdown, bg=_TV["bg_head"], bd=1, relief="solid")
        frame.pack(fill="both", expand=True)

        sb = tk.Scrollbar(frame, orient="vertical", bg=_TV["bg_alt"],
                          troughcolor=_TV["bg"], width=10, relief="flat", bd=0)
        self._listbox = tk.Listbox(
            frame,
            bg=_TV["bg_alt"], fg=_TV["fg"],
            selectbackground=_TV["sel_bg"], selectforeground=_TV["sel_fg"],
            font=("Consolas", 12), relief="flat", borderwidth=0,
            activestyle="none", highlightthickness=0,
            yscrollcommand=sb.set,
        )
        sb.configure(command=self._listbox.yview)
        if len(filtered) > 10:
            sb.pack(side="right", fill="y")
        self._listbox.pack(side="left", fill="both", expand=True)

        for i, v in enumerate(filtered):
            self._listbox.insert("end", f"  {v}")
            bg = _TV["bg"] if i % 2 == 0 else _TV["bg_alt"]
            self._listbox.itemconfigure(i, background=bg)

        self._listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        self._listbox.bind("<Double-1>",        self._on_listbox_select)
        self._dropdown.bind("<FocusOut>",       self._on_focus_out)
        self._dropdown.lift()

        # Inchide la click oriunde in afara dropdown-ului
        try:
            self._bind_global = self.winfo_toplevel().bind(
                "<Button-1>", self._on_global_click, add="+"
            )
        except tk.TclError:
            pass

    def _refresh_dropdown(self):
        filtered = self._filtered()
        if not (self._dropdown and self._dropdown.winfo_exists()):
            if filtered:
                self._open_dropdown()
            return
        self._listbox.delete(0, "end")
        for i, v in enumerate(filtered):
            self._listbox.insert("end", f"  {v}")
            bg = _TV["bg"] if i % 2 == 0 else _TV["bg_alt"]
            self._listbox.itemconfigure(i, background=bg)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        w = self.winfo_width()
        rows = min(len(filtered), 10)
        h = rows * 26 + 6
        if h == 6:   # lista goala
            self._close_dropdown(); return
        self._dropdown.wm_geometry(f"{w}x{h}+{x}+{y}")

    def _on_listbox_select(self, _event):
        sel = self._listbox.curselection()
        if sel:
            self._select_item(self._listbox.get(sel[0]).strip())

    def _select_item(self, value: str):
        self._skip_trace = True
        self._var.set(value)
        self._skip_trace = False
        self._close_dropdown()
        if self._on_change:
            self._on_change(value)

    def _on_global_click(self, event):
        """Inchide dropdown-ul la click in afara lui."""
        if not (self._dropdown and self._dropdown.winfo_exists()):
            return
        try:
            dx, dy = self._dropdown.winfo_rootx(), self._dropdown.winfo_rooty()
            dw, dh = self._dropdown.winfo_width(), self._dropdown.winfo_height()
            if dx <= event.x_root <= dx + dw and dy <= event.y_root <= dy + dh:
                return  # click inauntrul dropdown-ului
            ex, ey = self.winfo_rootx(), self.winfo_rooty()
            ew, eh = self.winfo_width(), self.winfo_height()
            if ex <= event.x_root <= ex + ew and ey <= event.y_root <= ey + eh:
                return  # click pe combobox insusi
        except tk.TclError:
            pass
        self._close_dropdown()

    def _on_focus_out(self, _event):
        self.after(150, self._close_dropdown)

    def _close_dropdown(self):
        # Sterge binding-ul global inainte de a distruge dropdown-ul
        if self._bind_global:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._bind_global)
            except tk.TclError:
                pass
            self._bind_global = None
        if self._dropdown and self._dropdown.winfo_exists():
            self._dropdown.destroy()
        self._dropdown = None
        self._listbox  = None

    def get(self) -> str:
        return self._var.get().strip()

    def set(self, value: str) -> None:
        self._skip_trace = True
        self._var.set(value)
        self._skip_trace = False


# ══════════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.backend = Backend()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("PBInfo Tracker")
        self.geometry("1460x860")
        self.minsize(1120, 700)
        self._all_comboboxes: list[UserComboBox] = []
        self._apply_tree_style()
        self._build_ui()

    def _apply_tree_style(self) -> None:
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("PB.Treeview",
            background=_TV["bg"], foreground=_TV["fg"],
            fieldbackground=_TV["bg"], rowheight=_TV["row_h"],
            font=_TV["font"], borderwidth=0, relief="flat",
        )
        s.configure("PB.Treeview.Heading",
            background=_TV["bg_head"], foreground=_TV["fg_head"],
            font=_TV["head_font"], relief="flat", borderwidth=0, padding=(8, 6),
        )
        s.map("PB.Treeview",
            background=[("selected", _TV["sel_bg"])],
            foreground=[("selected", _TV["sel_fg"])],
        )
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"PB.{orient}.TScrollbar",
                background=_TV["bg_alt"], troughcolor=_TV["bg"],
                arrowcolor=_TV["fg_head"], borderwidth=0,
            )

    # ── Layout ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ════ SIDEBAR ════════════════════════════════════════════════
        self.sidebar = ctk.CTkFrame(self, width=274, corner_radius=0,
                                    fg_color=("#0d0d1a", "#0d0d1a"))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Header
        ctk.CTkLabel(self.sidebar, text="PBInfo Tracker",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w").pack(anchor="w", padx=16, pady=(22, 0))
        ctk.CTkLabel(self.sidebar, text="pbinfo.ro  ·  scraper",
            text_color="#404060", font=ctk.CTkFont(size=10),
            anchor="w").pack(anchor="w", padx=16, pady=(0, 12))

        # Headless switch in card
        sw_card = ctk.CTkFrame(self.sidebar, fg_color="#1a1a2e", corner_radius=8)
        sw_card.pack(fill="x", padx=12, pady=(0, 4))
        self.headless_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(sw_card, text="  Headless browser",
            variable=self.headless_var,
            font=ctk.CTkFont(size=11),
            button_color="#89b4fa",
            progress_color="#1d4ed8",
        ).pack(padx=10, pady=8)

        ctk.CTkLabel(self.sidebar, text="ACTUALIZARE DATE",
            text_color="#303050", font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w").pack(anchor="w", padx=16, pady=(14, 4))

        # Modern action buttons
        self._action_buttons: list[ctk.CTkButton] = []
        for label, cmd, fg, hov, tc in [
            ("🔄  Actualizeaza toti",   self._run_update_all,
             "#1d3a8a", "#2150c0", "#93c5fd"),
            ("👤  Actualizeaza 1 user", self._open_single_user_dialog,
             "#3b1f7a", "#5227a0", "#c4b5fd"),
        ]:
            b = ctk.CTkButton(
                self.sidebar, text=label, command=cmd,
                width=248, height=44, corner_radius=10,
                fg_color=fg, hover_color=hov, text_color=tc,
                font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
            )
            b.pack(padx=13, pady=3)
            self._action_buttons.append(b)

        ctk.CTkLabel(self.sidebar,
            text="💡 Comparatii si analize  →  tab Analiza",
            text_color="#303050", font=ctk.CTkFont(size=9), anchor="w",
        ).pack(anchor="w", padx=16, pady=(10, 0))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color="#1e1e30").pack(fill="x", padx=13, pady=(14, 6))

        # LOG — always visible, fills remaining sidebar space
        log_hdr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        log_hdr.pack(fill="x", padx=13, pady=(0, 3))
        ctk.CTkLabel(log_hdr, text="LOG",
            text_color="#303050", font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w").pack(side="left")
        for color, lbl in [(_LOG_COLORS["ok"], "ok"),
                            (_LOG_COLORS["warn"], "!"),
                            (_LOG_COLORS["err"], "err")]:
            ctk.CTkLabel(log_hdr, text=f"● {lbl}", text_color=color,
                font=ctk.CTkFont(size=11)).pack(side="right", padx=3)

        # Clear-log at the very bottom
        ctk.CTkButton(self.sidebar, text="🗑  Sterge log",
            fg_color="transparent", border_width=1, border_color="#1e1e30",
            text_color="#404060", hover_color="#1a1a2e",
            width=248, height=28, corner_radius=8,
            command=self._clear_log,
        ).pack(side="bottom", padx=13, pady=(4, 14))

        self.log_box = ctk.CTkTextbox(
            self.sidebar, state="disabled",
            font=ctk.CTkFont(family="Consolas", size=9),
            corner_radius=8, fg_color="#080810",
            text_color="#6b7280",
        )
        self.log_box.pack(fill="both", expand=True, padx=11, pady=(0, 2))
        tb = self.log_box._textbox
        for key, color in _LOG_COLORS.items():
            tb.tag_config(key, foreground=color)

        # ════ CONTENT ════════════════════════════════════════════════
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True)

        # Progress strip at top
        pstrip = ctk.CTkFrame(content, fg_color="#0d0d1a", corner_radius=0, height=56)
        pstrip.pack(fill="x")
        pstrip.pack_propagate(False)
        pi = ctk.CTkFrame(pstrip, fg_color="transparent")
        pi.pack(fill="both", expand=True, padx=16, pady=10)
        self.status_label = ctk.CTkLabel(pi, text="Gata de utilizare.",
            anchor="w", font=ctk.CTkFont(size=10), text_color="#404060")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.progress_bar = ctk.CTkProgressBar(pi, height=14, corner_radius=7,
            width=220, progress_color="#1d4ed8", fg_color="#1a1a2e")
        self.progress_bar.pack(side="right")
        self.progress_bar.set(0)

        # Tabs
        self.tabs = ctk.CTkTabview(content, corner_radius=8,
                                   fg_color=("#16162a", "#16162a"),
                                   segmented_button_fg_color="#0d0d1a",
                                   segmented_button_selected_color="#1d4ed8",
                                   segmented_button_selected_hover_color="#2563eb",
                                   segmented_button_unselected_color="#0d0d1a",
                                   segmented_button_unselected_hover_color="#1a1a2e",
                                   text_color="#89b4fa",
                                   command=self._close_all_dropdowns)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        for name in ("👤  Profiluri", "📊  ProblemeAll", "🔍  Analiza", "📁  Fisiere CSV"):
            self.tabs.add(name)

        self._build_profile_tab(self.tabs.tab("👤  Profiluri"))
        self._build_probleme_all_tab(self.tabs.tab("📊  ProblemeAll"))
        self._build_analysis_tab(self.tabs.tab("🔍  Analiza"))
        self._build_files_tab(self.tabs.tab("📁  Fisiere CSV"))

    # ── Tab Profiluri ────────────────────────────────────────────────

    def _build_profile_tab(self, parent) -> None:
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(ctrl, text="Utilizator:",
            font=ctk.CTkFont(size=11)).pack(side="left", padx=(4, 6))
        self._prof_user_var = ctk.StringVar(value=self.backend.USERNAMES[0])
        _cb = UserComboBox(ctrl, values=self.backend.USERNAMES,
                     variable=self._prof_user_var, width=260,
        )
        _cb.pack(side="left", padx=4)
        self._all_comboboxes.append(_cb)
        ctk.CTkButton(ctrl, text="⟳ Incarca", width=100, height=34,
            corner_radius=8, fg_color="#1d3a8a", hover_color="#2150c0",
            text_color="#93c5fd", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._load_profile,
        ).pack(side="left", padx=6)
        self._stat_solved = ctk.CTkLabel(ctrl, text="✅ 0 rezolvate",
            fg_color="#1a2b1a", corner_radius=6, padx=9, pady=3,
            font=ctk.CTkFont(size=10))
        self._stat_solved.pack(side="left", padx=3)
        self._stat_failed = ctk.CTkLabel(ctrl, text="🔄 0 incercari",
            fg_color="#2d1b1b", corner_radius=6, padx=9, pady=3,
            font=ctk.CTkFont(size=10))
        self._stat_failed.pack(side="left", padx=3)
        self._stat_total = ctk.CTkLabel(ctrl, text="📊 0 total",
            fg_color="#1a1a2e", corner_radius=6, padx=9, pady=3,
            font=ctk.CTkFont(size=10))
        self._stat_total.pack(side="left", padx=3)

        sfrow = ctk.CTkFrame(parent, fg_color="transparent")
        sfrow.pack(fill="x", pady=(2, 6))
        ctk.CTkLabel(sfrow, text="🔎").pack(side="left", padx=(4, 0))
        self._prof_search_var = ctk.StringVar()
        self._prof_search_var.trace_add("write", lambda *_: self._filter_profile())
        ctk.CTkEntry(sfrow, textvariable=self._prof_search_var,
            placeholder_text="Cauta problema...",
            width=260, height=30, corner_radius=8).pack(side="left", padx=6)
        self._prof_filter_var = ctk.StringVar(value="toate")
        for val, text in [("toate","Toate"),("rezolvata","✅ Rezolvate"),("incercare","🔄 Incercari")]:
            ctk.CTkRadioButton(sfrow, text=text,
                variable=self._prof_filter_var, value=val,
                command=self._filter_profile,
                font=ctk.CTkFont(size=11)).pack(side="left", padx=8)
        self._prof_count_lbl = ctk.CTkLabel(sfrow, text="",
            text_color="#404060", font=ctk.CTkFont(size=10))
        self._prof_count_lbl.pack(side="right", padx=12)

        self._prof_all_rows: list[tuple[str, str, str]] = []
        self._prof_tree = self._make_tree(parent,
            columns=("problema","link","status"),
            headings=("Problema","Link","Status"),
            widths=(270, 450, 130))
        self._prof_tree.tag_configure("rezolvata",
            background=_TV["solved_bg"], foreground=_TV["solved_fg"])
        self._prof_tree.tag_configure("incercare",
            background=_TV["inc_bg"], foreground=_TV["inc_fg"])
        self._prof_tree.bind("<Double-1>",
            lambda _e: self._open_link_from(self._prof_tree))
        ctk.CTkLabel(parent,
            text="↑  Dublu-click → deschide in browser",
            text_color="#303050", font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=6, pady=(3, 0))

    # ── Tab ProblemeAll ──────────────────────────────────────────────

    def _build_probleme_all_tab(self, parent) -> None:
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(ctrl, text="⟳ Reimprospateaza", width=160, height=34,
            corner_radius=8, fg_color="#0c4a44", hover_color="#0f6b62",
            text_color="#5eead4", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._load_probleme_all).pack(side="left", padx=4)
        self._pa_count_lbl = ctk.CTkLabel(ctrl, text="",
            text_color="#404060", font=ctk.CTkFont(size=10))
        self._pa_count_lbl.pack(side="left", padx=12)

        # Legenda
        leg = ctk.CTkFrame(ctrl, fg_color="transparent")
        leg.pack(side="right", padx=8)
        ctk.CTkLabel(leg, text="Dificultate estimata:",
            text_color="#404060", font=ctk.CTkFont(size=9)).pack(side="left", padx=(0,4))
        for color, label in [
            (_TV["diff5_fg"], "≥20 Usor"),
            (_TV["diff4_fg"], "10-19"),
            (_TV["diff3_fg"], "5-9"),
            (_TV["diff2_fg"], "2-4"),
            (_TV["diff1_fg"], "1 Greu"),
        ]:
            ctk.CTkLabel(leg, text=f"● {label}", text_color=color,
                font=ctk.CTkFont(size=9)).pack(side="left", padx=4)

        sfrow = ctk.CTkFrame(parent, fg_color="transparent")
        sfrow.pack(fill="x", pady=(2, 6))
        ctk.CTkLabel(sfrow, text="🔎").pack(side="left", padx=(4, 0))
        self._pa_search_var = ctk.StringVar()
        self._pa_search_var.trace_add("write", lambda *_: self._filter_probleme_all())
        ctk.CTkEntry(sfrow, textvariable=self._pa_search_var,
            placeholder_text="Cauta problema...",
            width=280, height=30, corner_radius=8).pack(side="left", padx=6)

        self._pa_all_rows: list[list] = []
        self._pa_tree = self._make_tree(parent,
            columns=("problema","link","nr"),
            headings=("Problema","Link","Nr. Rezolvari"),
            widths=(290, 440, 120))
        for tag, bg, fg in [
            ("diff5",_TV["diff5_bg"],_TV["diff5_fg"]),
            ("diff4",_TV["diff4_bg"],_TV["diff4_fg"]),
            ("diff3",_TV["diff3_bg"],_TV["diff3_fg"]),
            ("diff2",_TV["diff2_bg"],_TV["diff2_fg"]),
            ("diff1",_TV["diff1_bg"],_TV["diff1_fg"]),
        ]:
            self._pa_tree.tag_configure(tag, background=bg, foreground=fg)
        self._pa_tree.bind("<Double-1>",
            lambda _e: self._open_link_from(self._pa_tree))
        ctk.CTkLabel(parent,
            text="↑  Dublu-click → deschide in browser  |  Verde = usor (popular)  Rosu = rar (greu)",
            text_color="#303050", font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=6, pady=(3, 0))
        self.after(300, self._load_probleme_all)

    def _diff_tag(self, n: int) -> str:
        if n >= 20: return "diff5"
        if n >= 10: return "diff4"
        if n >= 5:  return "diff3"
        if n >= 2:  return "diff2"
        return "diff1"

    def _load_probleme_all(self) -> None:
        self._pa_all_rows = self.backend.load_probleme_all()
        self._pa_search_var.set("")
        self._filter_probleme_all()

    def _filter_probleme_all(self) -> None:
        query = self._pa_search_var.get().lower()
        tree  = self._pa_tree
        tree.delete(*tree.get_children())
        visible = 0
        for row in self._pa_all_rows:
            prob, link, nr = row[0], row[1], row[2]
            if query and query not in prob.lower() and query not in link.lower():
                continue
            tree.insert("", "end", values=(prob, link, nr),
                        tags=(self._diff_tag(nr),))
            visible += 1
        total = len(self._pa_all_rows)
        self._pa_count_lbl.configure(
            text=f"{visible}/{total} probleme" if query else f"{total} probleme")

    # ── Tab Analiza ──────────────────────────────────────────────────

    def _build_analysis_tab(self, parent) -> None:
        names = self.backend.USERNAMES
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=4, pady=(8, 0))
        ctk.CTkLabel(top_bar, text="Mod:",
            font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(4, 8))
        self._an_mode_seg = ctk.CTkSegmentedButton(top_bar,
            values=["⚖️  Compara utilizatori", "📚  Nerezolvate"],
            command=self._switch_an_mode,
            font=ctk.CTkFont(size=11), width=380,
            selected_color="#1d4ed8", selected_hover_color="#2563eb",
            unselected_color="#1a1a2e", unselected_hover_color="#252540")
        self._an_mode_seg.pack(side="left")
        self._an_mode_seg.set("⚖️  Compara utilizatori")

        card = ctk.CTkFrame(parent, fg_color="#0f0f1f", corner_radius=10)
        card.pack(fill="x", padx=4, pady=(10, 0))

        # Panoul COMPARA
        self._cmp_panel = ctk.CTkFrame(card, fg_color="transparent")
        r1 = ctk.CTkFrame(self._cmp_panel, fg_color="transparent")
        r1.pack(fill="x", padx=14, pady=(12,4))
        ctk.CTkLabel(r1, text="Utilizator principal:", width=155, anchor="w",
            font=ctk.CTkFont(size=11)).pack(side="left")
        self._cmp_u1 = ctk.StringVar(value=names[0])
        _cb1 = UserComboBox(r1, values=names, variable=self._cmp_u1, width=220)
        _cb1.pack(side="left", padx=6)
        self._all_comboboxes.append(_cb1)
        ctk.CTkLabel(r1, text="fata de:", width=50, anchor="w",
            font=ctk.CTkFont(size=11)).pack(side="left", padx=(10,0))
        self._cmp_u2 = ctk.StringVar(value=names[1])
        _cb2 = UserComboBox(r1, values=names, variable=self._cmp_u2, width=220)
        _cb2.pack(side="left", padx=6)
        self._all_comboboxes.append(_cb2)

        r2 = ctk.CTkFrame(self._cmp_panel, fg_color="transparent")
        r2.pack(fill="x", padx=14, pady=(2,4))
        ctk.CTkLabel(r2, text="Afiseaza:", width=155, anchor="w",
            font=ctk.CTkFont(size=11)).pack(side="left")
        self._cmp_dir = ctk.StringVar(value="u1_not_u2")
        for val, lbl in [
            ("u1_not_u2","Ce a rezolvat U1, nu U2 "),
            ("u2_not_u1","Ce a rezolvat U2, nu U1 "),
            ("both",     "Ce au rezolvat amandoi"),
        ]:
            ctk.CTkRadioButton(r2, text=lbl, variable=self._cmp_dir, value=val,
                font=ctk.CTkFont(size=11)).pack(side="left", padx=8)

        r3 = ctk.CTkFrame(self._cmp_panel, fg_color="transparent")
        r3.pack(fill="x", padx=14, pady=(4,12))
        ctk.CTkButton(r3, text="🔍  Analizeaza", width=145, height=34,
            corner_radius=8, fg_color="#1d3a8a", hover_color="#2150c0",
            text_color="#93c5fd", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._run_compare).pack(side="left", padx=4)
        ctk.CTkLabel(r3, text="Rezultatele apar in tabel. Click pe antet = sortare.",
            text_color="#303050", font=ctk.CTkFont(size=9)).pack(side="left", padx=10)
        self._cmp_panel.pack(fill="x")

        # Panoul NEREZOLVATE
        self._unr_panel = ctk.CTkFrame(card, fg_color="transparent")
        r1u = ctk.CTkFrame(self._unr_panel, fg_color="transparent")
        r1u.pack(fill="x", padx=14, pady=(12,4))
        ctk.CTkLabel(r1u, text="Utilizator:", width=155, anchor="w",
            font=ctk.CTkFont(size=11)).pack(side="left")
        self._unr_user = ctk.StringVar(value=names[0])
        _cb3 = UserComboBox(r1u, values=names, variable=self._unr_user, width=220)
        _cb3.pack(side="left", padx=6)
        self._all_comboboxes.append(_cb3)
        ctk.CTkLabel(self._unr_panel,
            text="Afiseaza problemele rezolvate de colegi dar nu de utilizatorul selectat.\n"
                 "Sortate dupa popularitate. Verde ≥5 rezolvari (usor)  Portocaliu ≤1 (rar/greu).",
            text_color="#303050", font=ctk.CTkFont(size=9),
            justify="left", anchor="w").pack(anchor="w", padx=14, pady=(0,4))
        r2u = ctk.CTkFrame(self._unr_panel, fg_color="transparent")
        r2u.pack(fill="x", padx=14, pady=(4,12))
        ctk.CTkButton(r2u, text="🔍  Calculeaza", width=145, height=34,
            corner_radius=8, fg_color="#1d3a8a", hover_color="#2150c0",
            text_color="#93c5fd", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._run_unresolved).pack(side="left", padx=4)
        ctk.CTkLabel(r2u, text="Rezultatele apar in tabel. Click pe antet = sortare.",
            text_color="#303050", font=ctk.CTkFont(size=9)).pack(side="left", padx=10)

        # Bara rezultate + export
        rbar = ctk.CTkFrame(parent, fg_color="transparent")
        rbar.pack(fill="x", padx=4, pady=(10,2))
        self._an_count_lbl = ctk.CTkLabel(rbar, text="Niciun rezultat inca.",
            text_color="#303050", font=ctk.CTkFont(size=10), anchor="w")
        self._an_count_lbl.pack(side="left", padx=4)
        self._an_export_btn = ctk.CTkButton(rbar, text="💾  Export CSV",
            width=120, height=28, state="disabled", corner_radius=8,
            fg_color="transparent", border_width=1, border_color="#1e1e30",
            text_color="#404060", hover_color="#1a1a2e",
            command=self._export_analysis)
        self._an_export_btn.pack(side="right", padx=6)
        ctk.CTkLabel(rbar, text="🔎").pack(side="right", padx=(0,2))
        self._an_search_var = ctk.StringVar()
        self._an_search_var.trace_add("write", lambda *_: self._filter_analysis())
        ctk.CTkEntry(rbar, textvariable=self._an_search_var,
            placeholder_text="Filtreaza rezultate...",
            width=250, height=28, corner_radius=8).pack(side="right", padx=4)

        self._an_all_rows:    list[list] = []
        self._an_export_data: list[list] = []
        self._an_export_hdrs: list[str]  = []
        self._an_export_file: str        = "export.csv"

        tc = ctk.CTkFrame(parent, fg_color=_TV["bg"], corner_radius=8)
        tc.pack(fill="both", expand=True, padx=4, pady=(2,2))
        self._an_tree = self._attach_tree(tc,
            columns=("problema","link","nr"),
            headings=("Problema","Link","Nr. Rezolvari"),
            widths=(290,420,120))
        self._an_tree.tag_configure("popular",
            background=_TV["pop_bg"], foreground=_TV["pop_fg"])
        self._an_tree.tag_configure("rare",
            background=_TV["rare_bg"], foreground=_TV["rare_fg"])
        self._an_tree.bind("<Double-1>",
            lambda _e: self._open_link_from(self._an_tree))
        ctk.CTkLabel(parent, text="↑  Dublu-click → deschide in browser",
            text_color="#303050", font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=6, pady=(2,0))

    # ── Tab Fisiere CSV ──────────────────────────────────────────────

    def _build_files_tab(self, parent) -> None:
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, pady=(6, 0))

        # Stanga: lista fisiere
        left = ctk.CTkFrame(main, fg_color="#0d0d1a", corner_radius=10, width=230)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="FISIERE CSV",
            text_color="#303050", font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w").pack(anchor="w", padx=12, pady=(12, 4))

        self._file_search_list_var = ctk.StringVar()
        self._file_search_list_var.trace_add("write", lambda *_: self._refresh_file_list())
        ctk.CTkEntry(left, textvariable=self._file_search_list_var,
            placeholder_text="🔎 Filtreaza fisiere...",
            height=28, corner_radius=6).pack(fill="x", padx=8, pady=(0,4))

        ctk.CTkButton(left, text="⟳ Reimprospateaza", height=26,
            corner_radius=6, fg_color="#1a1a2e", hover_color="#252540",
            text_color="#89b4fa", font=ctk.CTkFont(size=10),
            command=self._refresh_file_list).pack(fill="x", padx=8, pady=(0,8))

        self._file_list_frame = ctk.CTkScrollableFrame(
            left, fg_color="transparent", corner_radius=0)
        self._file_list_frame.pack(fill="both", expand=True, padx=4, pady=(0,8))
        self._file_btn_map: dict[str, ctk.CTkButton] = {}
        self._selected_file: str = ""

        # Dreapta: tabel
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True)

        tctl = ctk.CTkFrame(right, fg_color="transparent")
        tctl.pack(fill="x", pady=(0,4))
        self._file_name_lbl = ctk.CTkLabel(tctl, text="Niciun fisier selectat",
            text_color="#303050", font=ctk.CTkFont(size=11, weight="bold"), anchor="w")
        self._file_name_lbl.pack(side="left", padx=4)
        self._file_count_lbl = ctk.CTkLabel(tctl, text="",
            text_color="#404060", font=ctk.CTkFont(size=10))
        self._file_count_lbl.pack(side="right", padx=12)

        sfrow = ctk.CTkFrame(right, fg_color="transparent")
        sfrow.pack(fill="x", pady=(0,6))
        ctk.CTkLabel(sfrow, text="🔎").pack(side="left", padx=(4,0))
        self._file_tbl_search_var = ctk.StringVar()
        self._file_tbl_search_var.trace_add("write", lambda *_: self._filter_file_table())
        ctk.CTkEntry(sfrow, textvariable=self._file_tbl_search_var,
            placeholder_text="Cauta in tabel...",
            width=270, height=30, corner_radius=8).pack(side="left", padx=6)

        self._file_tree_frame = tk.Frame(right, background=_TV["bg"])
        self._file_tree_frame.pack(fill="both", expand=True)
        self._file_tree:    ttk.Treeview | None = None
        self._file_rows:    list[list[str]]      = []
        self._file_headers: list[str]            = []

        ctk.CTkLabel(right, text="↑  Dublu-click → deschide in browser",
            text_color="#303050", font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=6, pady=(3,0))

        self.after(200, self._refresh_file_list)

    # ── Factory Treeview ─────────────────────────────────────────────

    def _make_tree(self, parent, columns, headings, widths) -> ttk.Treeview:
        frame = ctk.CTkFrame(parent, fg_color=_TV["bg"], corner_radius=8)
        frame.pack(fill="both", expand=True)
        return self._attach_tree(frame, columns, headings, widths)

    def _make_tree_in_tk(self, parent: tk.Frame, columns, headings, widths) -> ttk.Treeview:
        return self._attach_tree(parent, columns, headings, widths)

    def _attach_tree(self, frame, columns, headings, widths) -> ttk.Treeview:
        tree = ttk.Treeview(frame, columns=columns, show="headings",
            style="PB.Treeview", selectmode="browse")
        vsb = ttk.Scrollbar(frame, orient="vertical",
            command=tree.yview, style="PB.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(frame, orient="horizontal",
            command=tree.xview, style="PB.Horizontal.TScrollbar")
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(fill="both", expand=True, padx=1, pady=1)
        for col, hd, w in zip(columns, headings, widths):
            tree.heading(col, text=f"{hd}  ↕",
                command=lambda c=col, t=tree: self._sort_tree(t, c, False))
            tree.column(col, width=w, minwidth=50, anchor="w")
        return tree

    def _sort_tree(self, tree: ttk.Treeview, col: str, reverse: bool) -> None:
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            data.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            tree.move(k, "", idx)
        # Update arrow on clicked column; reset others to ↕
        for c in tree["columns"]:
            current = tree.heading(c, "text")
            base = current.rstrip(" ↕↑↓")
            if c == col:
                arrow = "  ↑" if reverse else "  ↓"
            else:
                arrow = "  ↕"
            tree.heading(c, text=base + arrow)
        tree.heading(col, command=lambda: self._sort_tree(tree, col, not reverse))

    @staticmethod
    def _open_link_from(tree: ttk.Treeview) -> None:
        sel = tree.selection()
        if not sel:
            return
        for val in tree.item(sel[0], "values"):
            if isinstance(val, str) and val.startswith("http"):
                webbrowser.open(val)
                return

    # ── Logica Profiluri ─────────────────────────────────────────────

    def _load_profile(self) -> None:
        raw = self._prof_user_var.get().strip()
        idx = self.backend.resolve_username(raw)
        if idx < 0:
            self.log(f"⚠ Utilizatorul '{raw}' nu a fost gasit.")
            return
        username = self.backend.USERNAMES[idx]
        self._prof_all_rows = self.backend.load_user_profile(username)
        n_s = sum(1 for *_, s in self._prof_all_rows if s == "rezolvata")
        n_i = sum(1 for *_, s in self._prof_all_rows if s == "incercare")
        self._stat_solved.configure(text=f"✅ {n_s} rezolvate")
        self._stat_failed.configure(text=f"🔄 {n_i} incercari")
        self._stat_total.configure( text=f"📊 {n_s + n_i} total")
        self._prof_search_var.set("")
        self._filter_profile()

    def _filter_profile(self) -> None:
        query = self._prof_search_var.get().lower()
        filt  = self._prof_filter_var.get()
        tree  = self._prof_tree
        tree.delete(*tree.get_children())
        visible = 0
        for prob, link, status in self._prof_all_rows:
            if filt != "toate" and status != filt:
                continue
            if query and query not in prob.lower():
                continue
            label = "✅ rezolvata" if status == "rezolvata" else "🔄 incercare"
            tree.insert("", "end", values=(prob, link, label), tags=(status,))
            visible += 1
        total = len(self._prof_all_rows)
        self._prof_count_lbl.configure(
            text=f"{visible}/{total}" if (query or filt != "toate") else f"{total} randuri")

    # ── Logica Analiza ────────────────────────────────────────────────

    def _switch_an_mode(self, value: str) -> None:
        if "Compara" in value:
            self._unr_panel.pack_forget()
            self._cmp_panel.pack(fill="x")
        else:
            self._cmp_panel.pack_forget()
            self._unr_panel.pack(fill="x")
        self._an_all_rows = []; self._an_export_data = []
        self._an_tree.delete(*self._an_tree.get_children())
        self._an_count_lbl.configure(text="Niciun rezultat inca.")
        self._an_search_var.set("")
        self._an_export_btn.configure(state="disabled")

    def _resolve_user(self, raw: str, label: str) -> int:
        idx = self.backend.resolve_username(raw)
        if idx < 0:
            self.log(f"⚠ {label}: utilizatorul '{raw}' nu a fost gasit.")
        return idx

    def _run_compare(self) -> None:
        i1 = self._resolve_user(self._cmp_u1.get(), "U1")
        i2 = self._resolve_user(self._cmp_u2.get(), "U2")
        if i1 < 0 or i2 < 0:
            return
        if i1 == i2:
            self.log("⚠ Selecteaza doi utilizatori diferiti.")
            return
        direction = self._cmp_dir.get()
        data = self.backend.compare_users(i1, i2, self.log, direction)
        names = self.backend.USERNAMES
        u1, u2 = names[i1], names[i2]
        dir_label = {
            "u1_not_u2": f"rezolvate de {u1}, nerezolvate de {u2}",
            "u2_not_u1": f"rezolvate de {u2}, nerezolvate de {u1}",
            "both":      f"rezolvate de ambii ({u1} si {u2})",
        }.get(direction, "")
        self._an_all_rows = data; self._an_export_data = data
        self._an_export_hdrs = ["Problema","Link","Nr. Rezolvari"]
        self._an_export_file = f"Comparatie_{u1}_vs_{u2}.csv"
        self._an_search_var.set("")
        self._filter_analysis()
        n = len(data)
        self._an_count_lbl.configure(
            text=f"{n} problem{'a' if n==1 else 'e'} — {dir_label}")
        self._an_export_btn.configure(state="normal" if data else "disabled")

    def _run_unresolved(self) -> None:
        index = self._resolve_user(self._unr_user.get(), "Utilizator")
        if index < 0:
            return
        username = self.backend.USERNAMES[index]
        data = self.backend.unresolved_by_user(index, self.log)
        self._an_all_rows = data; self._an_export_data = data
        self._an_export_hdrs = ["Problema","Link","Nr. Rezolvari"]
        self._an_export_file = f"Nerezolvate_{username}.csv"
        self._an_search_var.set("")
        self._filter_analysis()
        if data:
            self._an_count_lbl.configure(
                text=f"{len(data)} probleme nerezolvate de {username}"
                     f"   |   max {data[0][2]}   min {data[-1][2]} rezolvari")
        else:
            self._an_count_lbl.configure(text="0 rezultate.")
        self._an_export_btn.configure(state="normal" if data else "disabled")

    def _filter_analysis(self) -> None:
        query  = self._an_search_var.get().lower()
        tree   = self._an_tree
        tree.delete(*tree.get_children())
        visible = 0
        is_unr = "Nerezolvate" in self._an_mode_seg.get()
        for row in self._an_all_rows:
            prob  = row[0] if len(row) > 0 else ""
            link  = row[1] if len(row) > 1 else ""
            count = row[2] if len(row) > 2 else 0
            if query and query not in prob.lower() and query not in link.lower():
                continue
            tag = ""
            if is_unr and isinstance(count, int):
                tag = "popular" if count >= 5 else ("rare" if count <= 1 else "")
            tree.insert("", "end",
                values=(prob, link, count if count else "—"),
                tags=(tag,) if tag else ())
            visible += 1
        total = len(self._an_all_rows)
        if query and total:
            self._an_count_lbl.configure(
                text=f"{visible}/{total} rezultate (filtrate dupa '{query}')")

    def _export_analysis(self) -> None:
        if not self._an_export_data:
            return
        self.backend.export_results(
            self._an_export_data, self._an_export_hdrs,
            self._an_export_file, self.log)
        self.after(150, self._refresh_file_list)

    # ── Logica Fisiere CSV ────────────────────────────────────────────

    def _refresh_file_list(self) -> None:
        query = self._file_search_list_var.get().strip().lower()
        files = self.backend.list_csv_files()
        if query:
            files = [f for f in files if query in f.lower()]

        for w in self._file_list_frame.winfo_children():
            w.destroy()
        self._file_btn_map.clear()

        if not files:
            ctk.CTkLabel(self._file_list_frame,
                text="Niciun fisier CSV gasit.",
                text_color="#303050", font=ctk.CTkFont(size=9),
            ).pack(anchor="w", padx=6, pady=4)
            return

        for fname in files:
            icon = ("📊" if fname == "ProblemeAll.csv"
                    else "📄" if "_" in fname else "👤")
            is_sel = fname == self._selected_file
            btn = ctk.CTkButton(
                self._file_list_frame,
                text=f"{icon}  {fname}",
                anchor="w", height=28, corner_radius=6,
                fg_color="#1d4ed8" if is_sel else "transparent",
                hover_color="#1a1a2e",
                text_color="#89b4fa" if is_sel else "#9090a0",
                font=ctk.CTkFont(size=9, weight="bold" if is_sel else "normal"),
                command=lambda f=fname: self._select_file(f),
            )
            btn.pack(fill="x", padx=4, pady=1)
            self._file_btn_map[fname] = btn

        if self._selected_file not in files and files:
            self._select_file(files[0])

    def _select_file(self, filepath: str) -> None:
        self._selected_file = filepath
        for fname, btn in self._file_btn_map.items():
            is_sel = fname == filepath
            btn.configure(
                fg_color="#1d4ed8" if is_sel else "transparent",
                text_color="#89b4fa" if is_sel else "#9090a0",
                font=ctk.CTkFont(size=9, weight="bold" if is_sel else "normal"),
            )
        self._load_csv_view(filepath)

    def _load_csv_view(self, filepath: str) -> None:
        self._file_name_lbl.configure(text=f"📄  {filepath}")
        headers, rows = self.backend.load_csv_file(filepath)
        if not headers:
            return
        self._file_headers = headers
        self._file_rows    = rows
        self._file_tbl_search_var.set("")
        self._rebuild_file_tree(headers)
        self._filter_file_table()

    def _rebuild_file_tree(self, headers: list[str]) -> None:
        for w in self._file_tree_frame.winfo_children():
            w.destroy()
        n     = len(headers)
        col_w = max(110, min(300, 860 // max(n, 1)))
        self._file_tree = self._make_tree_in_tk(
            self._file_tree_frame,
            columns  = tuple(f"c{i}" for i in range(n)),
            headings = tuple(headers),
            widths   = tuple(col_w for _ in headers),
        )
        self._file_tree.bind("<Double-1>",
            lambda _e: self._open_link_from(self._file_tree))

    def _filter_file_table(self) -> None:
        if self._file_tree is None:
            return
        query = self._file_tbl_search_var.get().lower()
        tree  = self._file_tree
        tree.delete(*tree.get_children())
        visible = 0
        for row in self._file_rows:
            if query and not any(query in cell.lower() for cell in row):
                continue
            tag = "even" if visible % 2 == 0 else "odd"
            tree.insert("", "end", values=row, tags=(tag,))
            visible += 1
        tree.tag_configure("even", background=_TV["bg"])
        tree.tag_configure("odd",  background=_TV["bg_alt"])
        total = len(self._file_rows)
        self._file_count_lbl.configure(
            text=f"{visible}/{total} randuri" if query else f"{total} randuri")

    # ── Logging ──────────────────────────────────────────────────────

    def log(self, message: str) -> None:
        self.after(0, self._insert_log, message)

    def _insert_log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        tb = self.log_box._textbox
        self.log_box.configure(state="normal")
        tb.insert("end", f"[{ts}] ", "ts")
        if   message.startswith("✔"):                         tag = "ok"
        elif message.startswith("❌"):                        tag = "err"
        elif message.startswith("⚠") or "privat" in message: tag = "warn"
        else:                                                  tag = "info"
        tb.insert("end", message + "\n", tag)
        self.log_box.configure(state="disabled")
        tb.see("end")

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Progress & status ────────────────────────────────────────────

    def set_progress(self, value: float) -> None:
        self.after(0, self.progress_bar.set, min(max(value, 0.0), 1.0))

    def set_status(self, text: str) -> None:
        self.after(0, lambda: self.status_label.configure(text=text))

    # ── Threading ────────────────────────────────────────────────────

    def _run_in_thread(self, fn) -> None:
        self._set_buttons("disabled")
        self.set_progress(0)
        threading.Thread(target=self._thread_wrapper, args=(fn,), daemon=True).start()

    def _thread_wrapper(self, fn) -> None:
        try:
            fn()
        except Exception as exc:
            self.log(f"❌ Eroare neasteptata: {exc}")
        finally:
            self.after(0, self._set_buttons, "normal")
            self.set_status("Gata.")
            self.after(150, self._refresh_file_list)
            self.after(300, self._load_probleme_all)

    def _close_all_dropdowns(self, *_) -> None:
        """Inchide toate dropdown-urile deschise (ex: la schimbarea tab-ului)."""
        for cb in self._all_comboboxes:
            cb._close_dropdown()

    def _set_buttons(self, state: str) -> None:
        for btn in self._action_buttons:
            btn.configure(state=state)

    # ── Callbacks butoane ─────────────────────────────────────────────

    def _run_update_all(self) -> None:
        hl = self.headless_var.get()
        def task():
            self.set_status("Se actualizeaza toti utilizatorii...")
            self.backend.update_all(self.log, self.set_progress, headless=hl)
            self.set_progress(1.0)
        self._run_in_thread(task)

    def _run_update_all_csv(self) -> None:
        def task():
            self.set_status("Se construieste ProblemeAll.csv ...")
            self.backend.update_probleme_all(self.log)
        self._run_in_thread(task)

    def _open_single_user_dialog(self) -> None:
        dlg = ctk.CTkToplevel(self)
        dlg.title("Actualizeaza utilizator")
        dlg.geometry("390x160")
        dlg.resizable(False, False)
        dlg.grab_set()
        ctk.CTkLabel(dlg, text="Selecteaza sau scrie utilizatorul:",
            font=ctk.CTkFont(size=12)).pack(pady=(20, 6))
        var = ctk.StringVar(value=self.backend.USERNAMES[0])
        _cb_dlg = UserComboBox(dlg, values=self.backend.USERNAMES,
                     variable=var, width=330)
        _cb_dlg.pack(pady=4)
        self._all_comboboxes.append(_cb_dlg)

        def confirm():
            raw = var.get().strip()
            idx = self.backend.resolve_username(raw)
            if idx < 0:
                self.log(f"⚠ Utilizatorul '{raw}' nu exista.")
                dlg.destroy(); return
            dlg.destroy()
            self._run_in_thread(lambda: (
                self.set_status(f"Actualizare {self.backend.USERNAMES[idx]}..."),
                self.backend.update_single(idx, self.log,
                                           headless=self.headless_var.get()),
            ))
        ctk.CTkButton(dlg, text="✔  Confirma", command=confirm,
            width=180, height=36, corner_radius=8,
            fg_color="#1d3a8a", hover_color="#2150c0",
            text_color="#93c5fd", font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(pady=12)


# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()