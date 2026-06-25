#!/usr/bin/env python3
"""
🍅 Pomodoro Timer - 桌面番茄钟
A feature-rich Pomodoro timer with a clean macOS-native interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import os
import json

# ─── Configuration ───────────────────────────────────────────────────────────
CONFIG_FILE = os.path.expanduser("~/.pomodoro_config.json")
DEFAULT_CONFIG = {
    "work_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "pomodoros_before_long_break": 4,
    "always_on_top": True,
    "show_notifications": True,
}

COLORS = {
    "bg": "#f5f0eb",
    "fg": "#3d3d3d",
    "accent": "#e07050",
    "accent_light": "#f0a080",
    "success": "#70b080",
    "warning_bg": "#fef6e4",
    "break_bg": "#eef4fb",
    "break_accent": "#5090e0",
    "white": "#ffffff",
    "gray": "#a0a0a0",
    "light_gray": "#e0ddd8",
    "clock_bg": "#faf6f2",
    "clock_border": "#e8e2da",
}


class PomodoroTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🍅 番茄钟")
        self.root.configure(bg=COLORS["bg"])
        self.load_config()

        # Window always on top
        if self.config["always_on_top"]:
            self.root.attributes("-topmost", True)

        # Window size & position
        self.root.geometry("360x580")
        self.root.resizable(False, False)
        self.center_window()

        # State
        self.state = "idle"  # idle | work | short_break | long_break | paused
        self.remaining_seconds = self.config["work_minutes"] * 60
        self.pomodoro_count = 0
        self.running = False
        self.paused = False
        self.current_session_type = "work"

        # Build UI
        self.build_ui()

        # Bind close button
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start update loop
        self.update_display()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                    self.config = {**DEFAULT_CONFIG, **saved}
            except Exception:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def center_window(self):
        self.root.update_idletasks()
        w = 360
        h = 580
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ─── UI Building ─────────────────────────────────────────────────────────

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)

        # ── Title ──
        title_frame = tk.Frame(self.root, bg=COLORS["bg"], height=60)
        title_frame.pack(fill="x", pady=(20, 2))
        tk.Label(
            title_frame,
            text="🍅 番茄钟",
            font=("Helvetica", 22, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["accent"],
        ).pack()

        # ── Current Time ──
        self.clock_label = tk.Label(
            title_frame,
            text="",
            font=("Helvetica", 13),
            bg=COLORS["bg"],
            fg=COLORS["gray"],
        )
        self.clock_label.pack()

        # ── Clock Face (prominent timer display) ──
        clock_face = tk.Frame(
            self.root,
            bg=COLORS["clock_bg"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["clock_border"],
            highlightthickness=1,
        )
        clock_face.pack(pady=(18, 10), padx=30, fill="x")

        # Timer text - big Label widget
        self.timer_label = tk.Label(
            clock_face,
            text="25:00",
            font=("Helvetica", 64, "bold"),
            bg=COLORS["clock_bg"],
            fg=COLORS["fg"],
        )
        self.timer_label.pack(pady=(28, 2))

        # Status text
        self.status_label = tk.Label(
            clock_face,
            text="准备开始 🍅",
            font=("Helvetica", 13),
            bg=COLORS["clock_bg"],
            fg=COLORS["gray"],
        )
        self.status_label.pack(pady=(0, 28))

        # ── Session Counter ──
        self.counter_label = tk.Label(
            self.root,
            text="",
            font=("Helvetica", 11),
            bg=COLORS["bg"],
            fg=COLORS["gray"],
        )
        self.counter_label.pack(pady=(2, 2))

        # ── Session Dots ──
        dots_frame = tk.Frame(self.root, bg=COLORS["bg"])
        dots_frame.pack(fill="x", pady=(2, 5))
        self.session_dots_frame = tk.Frame(dots_frame, bg=COLORS["bg"])
        self.session_dots_frame.pack()
        self.session_dots = []

        # ── Progress Ring ──
        canvas_frame = tk.Frame(self.root, bg=COLORS["bg"])
        canvas_frame.pack(pady=(2, 8))

        canvas_size = 160
        self.canvas = tk.Canvas(
            canvas_frame,
            width=canvas_size,
            height=canvas_size,
            bg=COLORS["bg"],
            highlightthickness=0,
        )
        self.canvas.pack()

        cx = cy = canvas_size // 2
        r = 65
        self.arc_bg = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=COLORS["light_gray"], width=6,
        )
        self.arc_progress = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=0,
            outline=COLORS["accent"], width=6,
            style="arc",
        )

        # Canvas status emoji
        self.canvas_status = self.canvas.create_text(
            cx, cy + 2,
            text="🍅",
            font=("Helvetica", 28),
            fill=COLORS["gray"],
        )

        # ── Buttons ──
        btn_frame = tk.Frame(self.root, bg=COLORS["bg"])
        btn_frame.pack(pady=(8, 5))

        self.start_btn = tk.Button(
            btn_frame, text="▶ 开始",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["accent"], fg=COLORS["white"],
            activebackground=COLORS["accent_light"], activeforeground=COLORS["white"],
            bd=0, padx=18, pady=6,
            command=self.start_timer,
        )
        self.start_btn.pack(side="left", padx=4)

        self.pause_btn = tk.Button(
            btn_frame, text="⏸ 暂停",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["accent_light"], fg=COLORS["white"],
            activebackground=COLORS["accent"], activeforeground=COLORS["white"],
            bd=0, padx=18, pady=6,
            state="disabled",
            command=self.pause_timer,
        )
        self.pause_btn.pack(side="left", padx=4)

        self.reset_btn = tk.Button(
            btn_frame, text="↺ 重置",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["light_gray"], fg=COLORS["fg"],
            activebackground=COLORS["gray"], activeforeground=COLORS["white"],
            bd=0, padx=18, pady=6,
            command=self.reset_timer,
        )
        self.reset_btn.pack(side="left", padx=4)

        # ── Settings ──
        settings_frame = tk.Frame(self.root, bg=COLORS["bg"])
        settings_frame.pack(pady=(5, 10))

        self.settings_btn = tk.Button(
            settings_frame, text="⚙ 设置",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["gray"], fg=COLORS["white"],
            activebackground=COLORS["accent"], activeforeground=COLORS["white"],
            bd=0, padx=20, pady=5,
            command=self.open_settings,
        )
        self.settings_btn.pack()

    def update_session_dots(self):
        for dot in self.session_dots:
            dot.destroy()
        self.session_dots = []

        count = self.config["pomodoros_before_long_break"]
        for i in range(count):
            color = COLORS["accent"] if i < self.pomodoro_count % count else COLORS["light_gray"]
            dot = tk.Label(
                self.session_dots_frame,
                text="●",
                font=("Helvetica", 16),
                bg=COLORS["bg"],
                fg=color,
            )
            dot.pack(side="left", padx=4)
            self.session_dots.append(dot)

        self.counter_label.config(text=f"{self.pomodoro_count} 个番茄完成")

    # ─── Timer Logic ─────────────────────────────────────────────────────────

    def start_timer(self):
        if self.state in ("idle", "paused"):
            if self.state == "idle":
                self.state = "work"
                self.current_session_type = "work"
                self.remaining_seconds = self.config["work_minutes"] * 60
            elif self.state == "paused":
                self.state = self.current_session_type

            self.running = True
            self.paused = False
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.update_ui_state()

    def pause_timer(self):
        if self.running:
            self.running = False
            self.paused = True
            self.state = "paused"
            self.start_btn.config(state="normal", text="▶ 继续", bg=COLORS["success"])
            self.pause_btn.config(state="disabled")
            self.update_ui_state()

    def reset_timer(self):
        self.running = False
        self.paused = False
        self.state = "idle"
        self.current_session_type = "work"
        self.remaining_seconds = self.config["work_minutes"] * 60
        self.start_btn.config(state="normal", text="▶ 开始", bg=COLORS["accent"])
        self.pause_btn.config(state="disabled")
        self.update_ui_state()

    def finish_session(self):
        self.running = False

        if self.current_session_type == "work":
            self.pomodoro_count += 1
            self.update_session_dots()

            if self.pomodoro_count % self.config["pomodoros_before_long_break"] == 0:
                self.state = "long_break"
                self.current_session_type = "long_break"
                self.remaining_seconds = self.config["long_break_minutes"] * 60
                self.show_notification("🍅 番茄完成!", "该休息一下了！长休息 ☕")
            else:
                self.state = "short_break"
                self.current_session_type = "short_break"
                self.remaining_seconds = self.config["short_break_minutes"] * 60
                self.show_notification("🍅 番茄完成!", "休息 5 分钟吧！")
        else:
            self.state = "idle"
            self.current_session_type = "work"
            self.remaining_seconds = self.config["work_minutes"] * 60
            self.show_notification("☕ 休息结束!", "开始下一个番茄吧！")

        self.start_btn.config(state="normal", text="▶ 开始", bg=COLORS["accent"])
        self.pause_btn.config(state="disabled")
        self.update_ui_state()

    def show_notification(self, title, message):
        if not self.config["show_notifications"]:
            return
        try:
            os.system(
                f'osascript -e \'display notification "{message}" with title "{title}" sound name "default"\''
            )
        except Exception:
            pass

    def update_ui_state(self):
        """Update background colors based on current state."""
        if self.state == "paused":
            bg_color = COLORS["bg"]
        elif self.current_session_type == "work":
            bg_color = COLORS["warning_bg"] if self.running else COLORS["bg"]
        else:
            bg_color = COLORS["break_bg"]

        self.root.configure(bg=bg_color)
        self.canvas.configure(bg=bg_color)

        arc_color = COLORS["accent"] if self.current_session_type == "work" else COLORS["break_accent"]
        self.canvas.itemconfig(self.arc_progress, outline=arc_color)

    # ─── Display Update ──────────────────────────────────────────────────────

    def update_display(self):
        if self.running and self.remaining_seconds > 0:
            self.remaining_seconds -= 1

        # Clock
        self.clock_label.config(text=time.strftime("%H:%M"))

        # Timer
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        self.timer_label.config(text=f"{mins:02d}:{secs:02d}")

        # Progress arc
        total = self.get_total_seconds()
        if total > 0:
            progress = (total - self.remaining_seconds) / total * 360
            self.canvas.itemconfig(self.arc_progress, extent=progress)

        # Status text and canvas emoji
        status_map = {
            "idle": ("准备开始", "🍅"),
            "paused": ("已暂停", "⏸"),
            "work": ("专注中...", "💪"),
            "short_break": ("休息一下", "☕"),
            "long_break": ("长休息", "🎉"),
        }
        text, emoji = status_map.get(self.state, ("", ""))
        self.status_label.config(text=f"{text} {emoji}")
        self.canvas.itemconfig(self.canvas_status, text=emoji)

        # Check timer end
        if self.running and self.remaining_seconds <= 0:
            self.finish_session()

        self.root.after(1000, self.update_display)

    def get_total_seconds(self):
        t = self.current_session_type
        if t == "work":
            return self.config["work_minutes"] * 60
        elif t == "short_break":
            return self.config["short_break_minutes"] * 60
        elif t == "long_break":
            return self.config["long_break_minutes"] * 60
        return self.config["work_minutes"] * 60

    # ─── Settings Window ─────────────────────────────────────────────────────

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("⚙ 设置")
        win.configure(bg=COLORS["bg"])
        win.geometry("350x400")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 400) // 2
        win.geometry(f"+{x}+{y}")

        tk.Label(
            win, text="⚙ 设置", font=("Helvetica", 18, "bold"),
            bg=COLORS["bg"], fg=COLORS["fg"],
        ).pack(pady=(20, 15))

        form_frame = tk.Frame(win, bg=COLORS["bg"])
        form_frame.pack(padx=30, fill="x")

        fields = [
            ("work_minutes", "🍅 工作时长 (分钟):", 1, 120),
            ("short_break_minutes", "☕ 短休息 (分钟):", 1, 30),
            ("long_break_minutes", "🎉 长休息 (分钟):", 1, 60),
            ("pomodoros_before_long_break", "📊 几个番茄后长休息:", 1, 10),
        ]

        self.settings_vars = {}
        row = 0
        for key, label_text, min_val, max_val in fields:
            tk.Label(
                form_frame, text=label_text,
                font=("Helvetica", 11),
                bg=COLORS["bg"], fg=COLORS["fg"],
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(8, 2))

            var = tk.StringVar(value=str(self.config[key]))
            self.settings_vars[key] = var

            vcmd = (win.register(lambda v, mn=min_val, mx=max_val: self.validate_int(v, mn, mx)), "%P")
            entry = ttk.Entry(
                form_frame, textvariable=var, width=8,
                font=("Helvetica", 11),
                validate="key", validatecommand=vcmd,
            )
            entry.grid(row=row + 1, column=0, sticky="w", pady=(0, 5))
            row += 2

        self.notify_var = tk.BooleanVar(value=self.config["show_notifications"])
        tk.Checkbutton(
            form_frame, text="显示系统通知",
            variable=self.notify_var,
            font=("Helvetica", 11),
            bg=COLORS["bg"], fg=COLORS["fg"],
            selectcolor=COLORS["white"],
            activebackground=COLORS["bg"],
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1

        self.topmost_var = tk.BooleanVar(value=self.config["always_on_top"])
        tk.Checkbutton(
            form_frame, text="窗口置顶",
            variable=self.topmost_var,
            font=("Helvetica", 11),
            bg=COLORS["bg"], fg=COLORS["fg"],
            selectcolor=COLORS["white"],
            activebackground=COLORS["bg"],
        ).grid(row=row, column=0, sticky="w", pady=(5, 15))

        btn_frame = tk.Frame(win, bg=COLORS["bg"])
        btn_frame.pack(pady=(5, 5))

        tk.Button(
            btn_frame, text="💾 保存",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["accent"], fg=COLORS["white"],
            bd=0, padx=20, pady=5,
            command=lambda: self.save_settings(win),
        ).pack(pady=(0, 5))

        tk.Button(
            win, text="取消",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["light_gray"], fg=COLORS["fg"],
            bd=0, padx=20, pady=5,
            command=win.destroy,
        ).pack(pady=(0, 15))

    def validate_int(self, value, min_val, max_val):
        if value == "":
            return True
        try:
            v = int(value)
            return min_val <= v <= max_val
        except ValueError:
            return False

    def save_settings(self, win):
        changed = False
        for key, var in self.settings_vars.items():
            val = int(var.get())
            if self.config[key] != val:
                self.config[key] = val
                changed = True

        self.config["show_notifications"] = self.notify_var.get()
        self.config["always_on_top"] = self.topmost_var.get()
        self.root.attributes("-topmost", self.config["always_on_top"])

        self.save_config()
        self.reset_timer()
        self.update_session_dots()

        win.destroy()
        if changed:
            messagebox.showinfo("设置已保存", "番茄钟设置已更新并保存 ✅")

    # ─── Close Handler ───────────────────────────────────────────────────────

    def on_close(self):
        if self.running:
            result = messagebox.askyesno(
                "确认关闭",
                "番茄钟正在运行，确定要关闭吗？\n当前进度将丢失。"
            )
            if not result:
                return
        self.root.destroy()

    def run(self):
        self.update_session_dots()
        self.root.mainloop()


if __name__ == "__main__":
    app = PomodoroTimer()
    app.run()
