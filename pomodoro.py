#!/usr/bin/env python3
"""
🍅 Pomodoro Timer - 桌面番茄钟
A feature-rich Pomodoro timer with a clean macOS-native interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import os
import json
from datetime import datetime, timedelta

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
    "success_bg": "#e8f5e9",
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
        self.root.attributes("-topmost", self.config["always_on_top"])

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
            except:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except:
            pass

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ─── UI Building ─────────────────────────────────────────────────────────

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)

        # --- Title ---
        title_frame = tk.Frame(self.root, bg=COLORS["bg"], height=60)
        title_frame.pack(fill="x", pady=(20, 2))
        tk.Label(
            title_frame,
            text="🍅 番茄钟",
            font=("Helvetica Neue", 22, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["accent"],
        ).pack()

        # --- Current Time ---
        self.clock_label = tk.Label(
            title_frame,
            text="",
            font=("Helvetica Neue", 13),
            bg=COLORS["bg"],
            fg=COLORS["gray"],
        )
        self.clock_label.pack()

        # --- Clock Face (prominent timer display) ---
        clock_face = tk.Frame(
            self.root,
            bg=COLORS["clock_bg"],
            bd=1,
            relief="solid",
            highlightbackground=COLORS["clock_border"],
            highlightcolor=COLORS["clock_border"],
            highlightthickness=1,
        )
        clock_face.pack(pady=(18, 10), padx=30, fill="x")

        # Timer text - using Label for reliability (not canvas text)
        self.timer_label = tk.Label(
            clock_face,
            text="25:00",
            font=("Helvetica Neue", 64, "bold"),
            bg=COLORS["clock_bg"],
            fg=COLORS["fg"],
        )
        self.timer_label.pack(pady=(28, 2))

        # Status text 1 (session type)
        self.status_label = tk.Label(
            clock_face,
            text="准备开始 🍅",
            font=("Helvetica Neue", 13),
            bg=COLORS["clock_bg"],
            fg=COLORS["gray"],
        )
        self.status_label.pack(pady=(0, 28))

        # --- Session Counter ---
        self.counter_label = tk.Label(
            self.root,
            text="",
            font=("Helvetica Neue", 11),
            bg=COLORS["bg"],
            fg=COLORS["gray"],
        )
        self.counter_label.pack(pady=(2, 2))

        # --- Session Dots ---
        self.status_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.status_frame.pack(fill="x", pady=(2, 5))
        self.session_dots_frame = tk.Frame(self.status_frame, bg=COLORS["bg"])
        self.session_dots_frame.pack()
        self.session_dots = []

        # --- Canvas / Progress Ring (visual decoration) ---
        self.canvas_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.canvas_frame.pack(pady=(2, 8))

        canvas_size = 160
        self.canvas = tk.Canvas(
            self.canvas_frame,
            width=canvas_size,
            height=canvas_size,
            bg=COLORS["bg"],
            highlightthickness=0,
        )
        self.canvas.pack()

        # Draw circular progress ring
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

        # Small status text on canvas
        self.canvas_status = self.canvas.create_text(
            cx, cy + 2,
            text="⏳",
            font=("Helvetica Neue", 28),
            fill=COLORS["gray"],
        )

        # --- Buttons ---
        btn_frame = tk.Frame(self.root, bg=COLORS["bg"])
        btn_frame.pack(pady=(8, 5))

        self.start_btn = self.create_button(
            btn_frame, "▶ 开始", COLORS["accent"], COLORS["white"], self.start_timer
        )
        self.start_btn.pack(side="left", padx=4)

        self.pause_btn = self.create_button(
            btn_frame, "⏸ 暂停", COLORS["accent_light"], COLORS["white"],
            self.pause_timer, state="disabled"
        )
        self.pause_btn.pack(side="left", padx=4)

        self.reset_btn = self.create_button(
            btn_frame, "↺ 重置", COLORS["light_gray"], COLORS["fg"], self.reset_timer
        )
        self.reset_btn.pack(side="left", padx=4)

        # --- Settings Button ---
        settings_frame = tk.Frame(self.root, bg=COLORS["bg"])
        settings_frame.pack(pady=(8, 5))

        self.settings_btn = self.create_button(
            settings_frame, "⚙ 设置", COLORS["gray"], COLORS["white"],
            self.open_settings
        )
        self.settings_btn.pack()

    def create_button(self, parent, text, bg, fg, command, state="normal"):
        btn = tk.Button(
            parent,
            text=text,
            font=("Helvetica Neue", 11, "bold"),
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            state=state,
            disabledforeground=COLORS["gray"],
            command=command,
        )
        btn.config(relief="flat", highlightthickness=0)
        return btn

    def update_session_dots(self):
        for dot in self.session_dots:
            dot.destroy()
        self.session_dots = []

        count = self.config["pomodoros_before_long_break"]
        for i in range(count):
            if i < self.pomodoro_count % count:
                color = COLORS["accent"]
            else:
                color = COLORS["light_gray"]
            dot = tk.Label(
                self.session_dots_frame,
                text="●",
                font=("Helvetica Neue", 16),
                bg=COLORS["bg"],
                fg=color,
            )
            dot.pack(side="left", padx=4)
            self.session_dots.append(dot)

        txt = f"{self.pomodoro_count} 个番茄完成"
        self.counter_label.config(text=txt)

    # ─── Timer Logic ─────────────────────────────────────────────────────────

    def start_timer(self):
        if self.state == "idle" or self.state == "paused":
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
            self.start_btn.config(state="normal")
            self.start_btn.config(text="▶ 继续", bg=COLORS["success"])
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
                self.show_notification("🍅 番茄完成!", "该休息一下了！长休息 15 分钟 ☕")
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
        except:
            pass

    def update_ui_state(self):
        """Update background colors based on current state."""
        if self.current_session_type == "work":
            if self.running:
                self.root.configure(bg=COLORS["warning_bg"])
                self.canvas.configure(bg=COLORS["warning_bg"])
                self.canvas_frame.configure(bg=COLORS["warning_bg"])
            else:
                self.root.configure(bg=COLORS["bg"])
                self.canvas.configure(bg=COLORS["bg"])
                self.canvas_frame.configure(bg=COLORS["bg"])
            self.canvas.itemconfig(self.arc_progress, outline=COLORS["accent"])
        else:
            self.root.configure(bg=COLORS["break_bg"])
            self.canvas.configure(bg=COLORS["break_bg"])
            self.canvas_frame.configure(bg=COLORS["break_bg"])
            self.canvas.itemconfig(self.arc_progress, outline=COLORS["break_accent"])

        # Update all background-dependent widgets
        for widget in [self.status_frame, self.session_dots_frame,
                       self.counter_label, self.status_frame]:
            try:
                widget.configure(bg=self.root.cget("bg"))
            except:
                pass

    # ─── Display Update ──────────────────────────────────────────────────────

    def update_display(self):
        if self.running and self.remaining_seconds > 0:
            self.remaining_seconds -= 1

        # Update clock
        now = time.strftime("%H:%M")
        self.clock_label.config(text=now)

        # Update timer text (Label widget - reliable)
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")

        # Update progress arc
        total = self.get_total_seconds()
        if total > 0:
            progress = (total - self.remaining_seconds) / total * 360
            self.canvas.itemconfig(self.arc_progress, extent=progress)

        # Update status text and canvas emoji
        if self.state == "idle":
            if self.current_session_type == "work":
                self.status_label.config(text="准备开始 🍅")
                self.canvas.itemconfig(self.canvas_status, text="🍅")
            elif self.current_session_type == "short_break":
                self.status_label.config(text="休息一下 ☕")
                self.canvas.itemconfig(self.canvas_status, text="☕")
            elif self.current_session_type == "long_break":
                self.status_label.config(text="长休息 🎉")
                self.canvas.itemconfig(self.canvas_status, text="🎉")
        elif self.state == "paused":
            self.status_label.config(text="已暂停 ⏸")
            self.canvas.itemconfig(self.canvas_status, text="⏸")
        elif self.state == "work":
            self.status_label.config(text="专注中... 💪")
            self.canvas.itemconfig(self.canvas_status, text="🍅")
        elif self.state == "short_break":
            self.status_label.config(text="休息一下 ☕")
            self.canvas.itemconfig(self.canvas_status, text="☕")
        elif self.state == "long_break":
            self.status_label.config(text="长休息 🎉")
            self.canvas.itemconfig(self.canvas_status, text="🎉")

        # Check if timer finished
        if self.running and self.remaining_seconds <= 0:
            self.finish_session()

        # Update every 1 second
        self.root.after(1000, self.update_display)

    def get_total_seconds(self):
        if self.current_session_type == "work":
            return self.config["work_minutes"] * 60
        elif self.current_session_type == "short_break":
            return self.config["short_break_minutes"] * 60
        elif self.current_session_type == "long_break":
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
            win, text="⚙ 设置", font=("Helvetica Neue", 18, "bold"),
            bg=COLORS["bg"], fg=COLORS["fg"]
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
                font=("Helvetica Neue", 11),
                bg=COLORS["bg"], fg=COLORS["fg"],
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(8, 2))

            var = tk.StringVar(value=str(self.config[key]))
            self.settings_vars[key] = var

            validate_cmd = win.register(lambda v, mn=min_val, mx=max_val: self.validate_int(v, mn, mx))
            entry = ttk.Entry(
                form_frame, textvariable=var, width=8,
                font=("Helvetica Neue", 11),
                validate="key", validatecommand=(validate_cmd, "%P"),
            )
            entry.grid(row=row + 1, column=0, sticky="w", pady=(0, 5))
            row += 2

        self.notify_var = tk.BooleanVar(value=self.config["show_notifications"])
        tk.Checkbutton(
            form_frame, text="显示系统通知",
            variable=self.notify_var,
            font=("Helvetica Neue", 11),
            bg=COLORS["bg"], fg=COLORS["fg"],
            selectcolor=COLORS["white"],
            activebackground=COLORS["bg"],
        ).grid(row=row, column=0, sticky="w", pady=(10, 5))
        row += 1

        self.topmost_var = tk.BooleanVar(value=self.config["always_on_top"])
        tk.Checkbutton(
            form_frame, text="窗口置顶",
            variable=self.topmost_var,
            font=("Helvetica Neue", 11),
            bg=COLORS["bg"], fg=COLORS["fg"],
            selectcolor=COLORS["white"],
            activebackground=COLORS["bg"],
        ).grid(row=row, column=0, sticky="w", pady=(5, 15))

        btn_save = self.create_button(
            win, "💾 保存", COLORS["accent"], COLORS["white"], lambda: self.save_settings(win)
        )
        btn_save.pack(pady=(5, 5))

        btn_cancel = self.create_button(
            win, "取消", COLORS["light_gray"], COLORS["fg"], win.destroy
        )
        btn_cancel.pack(pady=(0, 15))

    def validate_int(self, value, min_val, max_val):
        if value == "":
            return True
        try:
            v = int(value)
            return min_val <= v <= max_val
        except:
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
