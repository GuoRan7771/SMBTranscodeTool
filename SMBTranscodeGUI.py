#!/usr/bin/env python3
# SMB-Compatible GPU Transcoder with Realtime Progress (macOS)
# Author: Guo
# Requirements: Python 3, ffmpeg (brew install ffmpeg)

import os, sys, threading, subprocess, time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# ----------------------- ffmpeg command -----------------------
def build_ffmpeg_cmd(in_path: Path, out_path: Path, v_bitrate: str, a_bitrate: str, a_sr: str):
    return [
        "ffmpeg",
        "-hide_banner", "-y",
        "-hwaccel", "videotoolbox",
        "-i", str(in_path),
        "-c:v", "h264_videotoolbox",
        "-b:v", v_bitrate,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", a_bitrate,
        "-ar", a_sr,
        "-progress", "pipe:1",  # 输出机器可解析的进度信息
        "-nostats",
        str(out_path)
    ]

# ----------------------- GUI Worker -----------------------
class Transcoder(threading.Thread):
    def __init__(self, ui):
        super().__init__(daemon=True)
        self.ui = ui
        self.stop_flag = False

    def run(self):
        ui = self.ui
        input_dir = Path(ui.input_dir_var.get()).expanduser()
        output_dir = Path(ui.output_dir_var.get()).expanduser()
        overwrite = ui.overwrite_var.get() == 1
        v_bitrate, a_bitrate, a_sr = ui.v_bitrate_var.get(), ui.a_bitrate_var.get(), ui.a_sr_var.get()
        recurse = ui.recurse_var.get() == 1
        exts = [".mp4", ".mkv", ".mov", ".avi"]

        if not input_dir.is_dir():
            ui.log("无效的输入目录")
            ui.set_running(False)
            return
        if not overwrite and not output_dir:
            ui.log("未选择输出目录")
            ui.set_running(False)
            return
        if not overwrite:
            output_dir.mkdir(parents=True, exist_ok=True)

        files = list(input_dir.rglob("*") if recurse else input_dir.glob("*"))
        files = [f for f in files if f.suffix.lower() in exts]
        if not files:
            ui.log("未发现可转码文件")
            ui.set_running(False)
            return

        total = len(files)
        ui.log(f"共 {total} 个文件。")

        for idx, in_path in enumerate(files, 1):
            if self.stop_flag:
                ui.log("已中止。")
                break
            rel = in_path.relative_to(input_dir)
            if overwrite:
                out_path = in_path.with_suffix(".tmp.smbfix.mp4")
            else:
                out_path = (output_dir / rel).with_suffix(".mp4")
                out_path.parent.mkdir(parents=True, exist_ok=True)

            ui.log(f"[{idx}/{total}] ⏳ 开始转码：{in_path.name}")
            ui.progress_var.set(f"{idx}/{total} {in_path.name}")

            cmd = build_ffmpeg_cmd(in_path, out_path, v_bitrate, a_bitrate, a_sr)
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            last_time = ""
            for line in process.stdout:
                if self.stop_flag:
                    process.kill()
                    ui.log("已强制终止。")
                    break
                if line.startswith("out_time="):
                    t = line.strip().split("=")[-1]
                    last_time = t
                    ui.progress_var.set(f"{idx}/{total} {in_path.name} → {t}")
                elif line.startswith("progress=end"):
                    ui.log(f"✅ 完成 {in_path.name} （时长 {last_time}）")
                    break

            process.wait()
            if process.returncode == 0:
                if overwrite:
                    try:
                        in_path.unlink(missing_ok=False)
                        out_path.rename(in_path)
                        ui.log(f"已覆盖原文件：{in_path}")
                    except Exception as e:
                        ui.log(f"覆盖失败: {e}")
                else:
                    ui.log(f"输出: {out_path}")
            else:
                ui.log(f"❌ 转码失败：{in_path.name}")

        ui.log("任务结束。")
        ui.progress_var.set("完成。")
        ui.set_running(False)

# ----------------------- GUI -----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMB兼容视频批量转码器（GPU+实时进度）")
        self.geometry("780x600")

        self.input_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.v_bitrate_var = tk.StringVar(value="5M")
        self.a_bitrate_var = tk.StringVar(value="128k")
        self.a_sr_var = tk.StringVar(value="44100")
        self.overwrite_var = tk.IntVar(value=0)
        self.recurse_var = tk.IntVar(value=1)
        self.progress_var = tk.StringVar(value="待命")
        self.running = False
        self.worker = None

        self.make_widgets()

    def make_widgets(self):
        pad = {"padx": 8, "pady": 6}

        fr_in = tk.LabelFrame(self, text="输入目录")
        fr_in.pack(fill="x", **pad)
        tk.Entry(fr_in, textvariable=self.input_dir_var).pack(side="left", fill="x", expand=True, padx=6)
        tk.Button(fr_in, text="选择…", command=self.choose_input).pack(side="left", padx=6)

        fr_out = tk.LabelFrame(self, text="输出目录")
        fr_out.pack(fill="x", **pad)
        tk.Entry(fr_out, textvariable=self.output_dir_var).pack(side="left", fill="x", expand=True, padx=6)
        tk.Button(fr_out, text="选择…", command=self.choose_output).pack(side="left", padx=6)
        tk.Checkbutton(fr_out, text="覆盖原文件", variable=self.overwrite_var).pack(side="left", padx=10)

        fr_args = tk.LabelFrame(self, text="参数")
        fr_args.pack(fill="x", **pad)
        tk.Label(fr_args, text="视频码率").grid(row=0, column=0, sticky="e")
        tk.Entry(fr_args, width=8, textvariable=self.v_bitrate_var).grid(row=0, column=1)
        tk.Label(fr_args, text="音频码率").grid(row=0, column=2, sticky="e")
        tk.Entry(fr_args, width=8, textvariable=self.a_bitrate_var).grid(row=0, column=3)
        tk.Label(fr_args, text="采样率").grid(row=0, column=4, sticky="e")
        tk.Entry(fr_args, width=8, textvariable=self.a_sr_var).grid(row=0, column=5)
        tk.Checkbutton(fr_args, text="递归子目录", variable=self.recurse_var).grid(row=0, column=6, padx=10)

        fr_ctl = tk.Frame(self)
        fr_ctl.pack(fill="x", **pad)
        self.btn_start = tk.Button(fr_ctl, text="开始", command=self.start)
        self.btn_stop = tk.Button(fr_ctl, text="停止", command=self.stop, state="disabled")
        self.btn_start.pack(side="left")
        self.btn_stop.pack(side="left", padx=8)
        tk.Label(fr_ctl, textvariable=self.progress_var, anchor="w").pack(side="left", padx=20)

        fr_log = tk.LabelFrame(self, text="日志")
        fr_log.pack(fill="both", expand=True, **pad)
        self.log_box = scrolledtext.ScrolledText(fr_log, height=20)
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def choose_input(self):
        d = filedialog.askdirectory(title="选择输入目录")
        if d: self.input_dir_var.set(d)

    def choose_output(self):
        d = filedialog.askdirectory(title="选择输出目录")
        if d: self.output_dir_var.set(d)

    def start(self):
        if self.running:
            return
        if not which("ffmpeg"):
            messagebox.showerror("缺少ffmpeg", "请先执行: brew install ffmpeg")
            return
        self.set_running(True)
        self.worker = Transcoder(self)
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.stop_flag = True

    def set_running(self, running: bool):
        self.running = running
        self.btn_start.config(state="disabled" if running else "normal")
        self.btn_stop.config(state="normal" if running else "disabled")

    def log(self, s: str):
        self.log_box.insert(tk.END, s + "\n")
        self.log_box.see(tk.END)

def which(cmd):
    for p in os.environ["PATH"].split(os.pathsep):
        fp = Path(p) / cmd
        if fp.exists() and os.access(fp, os.X_OK):
            return str(fp)
    return None

if __name__ == "__main__":
    App().mainloop()
