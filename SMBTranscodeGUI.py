#!/usr/bin/env python3
# SMB-Compatible GPU Transcoder (GUI with Presets)
# macOS + VideoToolbox GPU + Realtime progress + Skip detection
# Author: Guo
import os, subprocess, threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# ---------- basic helpers ----------
def which(cmd):
    for p in os.environ["PATH"].split(os.pathsep):
        fp = Path(p) / cmd
        if fp.exists() and os.access(fp, os.X_OK):
            return str(fp)
    return None

def ffprobe_info(path: Path):
    try:
        out = subprocess.check_output([
            "ffprobe","-v","error",
            "-select_streams","v:0",
            "-show_entries","stream=codec_name,pix_fmt",
            "-of","csv=p=0", str(path)
        ], text=True)
        vcodec, pixfmt = out.strip().split(",")
        aout = subprocess.check_output([
            "ffprobe","-v","error",
            "-select_streams","a:0",
            "-show_entries","stream=codec_name",
            "-of","csv=p=0", str(path)
        ], text=True)
        acodec = aout.strip()
        return vcodec, pixfmt, acodec
    except Exception:
        return "", "", ""

def is_smb_ok(v,a,p): return (v in ["h264","mpeg4"]) and (p=="yuv420p") and (a in ["aac","mp3"])

def build_ffmpeg_cmd(i,o,vb,ab,sr):
    return ["ffmpeg","-hide_banner","-y","-hwaccel","videotoolbox","-i",str(i),
            "-c:v","h264_videotoolbox","-b:v",vb,"-pix_fmt","yuv420p",
            "-movflags","+faststart","-c:a","aac","-b:a",ab,"-ar",sr,
            "-progress","pipe:1","-nostats",str(o)]

# ---------- worker ----------
class Worker(threading.Thread):
    def __init__(self,ui): super().__init__(daemon=True); self.ui=ui; self.stop=False
    def run(self):
        ui=self.ui
        indir=Path(ui.in_dir.get()).expanduser()
        outdir=Path(ui.out_dir.get()).expanduser()
        overwrite=ui.overwrite.get()==1
        quality=ui.quality.get()
        vbit,a_bit,sr = ui.presets[quality]
        files=[f for f in (indir.rglob("*") if ui.recursive.get() else indir.glob("*"))
               if f.suffix.lower() in [".mp4",".mkv",".mov",".avi"]]
        if not files: ui.log("无可转码文件"); ui.set_run(False);return
        ui.log(f"共 {len(files)} 个文件。")
        for idx,f in enumerate(files,1):
            if self.stop:break
            v,a,p=ffprobe_info(f)
            if is_smb_ok(v,a,p):
                ui.log(f"[{idx}/{len(files)}] ✅ 跳过(已兼容) {f.name}")
                continue
            rel=f.relative_to(indir)
            out=f.with_suffix(".tmp.smbfix.mp4") if overwrite else (outdir/rel).with_suffix(".mp4")
            out.parent.mkdir(parents=True,exist_ok=True)
            ui.log(f"[{idx}/{len(files)}] ⏳ 转码 {f.name} ({v}/{a}/{p})")
            cmd=build_ffmpeg_cmd(f,out,vbit,a_bit,sr)
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in proc.stdout:
                if self.stop:proc.kill();break
                if line.startswith("out_time="):
                    ui.progress.set(f"{idx}/{len(files)} {f.name} → {line.strip().split('=')[-1]}")
            proc.wait()
            if proc.returncode==0:
                if overwrite:
                    try:f.unlink();out.rename(f);ui.log(f"完成并覆盖 {f}")
                    except Exception as e:ui.log(f"覆盖失败 {e}")
                else:ui.log(f"输出: {out}")
            else:ui.log(f"❌ 失败 {f.name}")
        ui.log("任务结束。");ui.set_run(False);ui.progress.set("完成")

# ---------- GUI ----------
class GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMB兼容视频批量转码器（GPU + 预设 + 实时进度）")
        self.geometry("780x640")
        self.in_dir=tk.StringVar(); self.out_dir=tk.StringVar()
        self.overwrite=tk.IntVar(value=0); self.recursive=tk.IntVar(value=1)
        self.progress=tk.StringVar(value="待命")
        self.quality=tk.StringVar(value="标准 (5 M / 128 k / 44.1 kHz)")
        # 预设：{显示名: (vbitrate, abit, samplerate)}
        self.presets={
            "低画质 (2 M / 96 k / 32 kHz)":("2M","96k","32000"),
            "标准 (5 M / 128 k / 44.1 kHz)":("5M","128k","44100"),
            "高画质 (8 M / 192 k / 48 kHz)":("8M","192k","48000"),
            "超清 (12 M / 256 k / 48 kHz)":("12M","256k","48000")
        }
        self.make_ui(); self.worker=None; self.running=False
        self.log("选择质量预设可自动匹配推荐参数。")

    # ----- UI -----
    def make_ui(self):
        pad={"padx":8,"pady":6}
        fi=tk.LabelFrame(self,text="输入目录"); fi.pack(fill="x",**pad)
        tk.Entry(fi,textvariable=self.in_dir).pack(side="left",fill="x",expand=True,padx=6)
        tk.Button(fi,text="选择…",command=lambda:self.sel_dir(self.in_dir)).pack(side="left",padx=6)
        fo=tk.LabelFrame(self,text="输出目录"); fo.pack(fill="x",**pad)
        tk.Entry(fo,textvariable=self.out_dir).pack(side="left",fill="x",expand=True,padx=6)
        tk.Button(fo,text="选择…",command=lambda:self.sel_dir(self.out_dir)).pack(side="left",padx=6)
        tk.Checkbutton(fo,text="覆盖原文件",variable=self.overwrite).pack(side="left",padx=10)
        fr=tk.LabelFrame(self,text="参数预设"); fr.pack(fill="x",**pad)
        tk.Label(fr,text="质量等级:").pack(side="left",padx=6)
        tk.OptionMenu(fr,self.quality,*self.presets.keys()).pack(side="left")
        tk.Checkbutton(fr,text="递归子目录",variable=self.recursive).pack(side="left",padx=20)
        rec=tk.LabelFrame(self,text="预设说明")
        rec.pack(fill="x",**pad)
        tk.Label(rec,justify="left",text=
            "推荐：\n"
            "• 低画质：体积最小，适合语音录像\n"
            "• 标准：一般视频/课程录制（默认）\n"
            "• 高画质：720p~1080p\n"
            "• 超清：4K 或高码率素材"
        ).pack(anchor="w",padx=10)
        fc=tk.Frame(self); fc.pack(fill="x",**pad)
        self.bstart=tk.Button(fc,text="开始",command=self.start)
        self.bstop=tk.Button(fc,text="停止",command=self.stop,state="disabled")
        self.bstart.pack(side="left"); self.bstop.pack(side="left",padx=8)
        tk.Label(fc,textvariable=self.progress,anchor="w").pack(side="left",padx=20)
        flog=tk.LabelFrame(self,text="日志"); flog.pack(fill="both",expand=True,**pad)
        self.box=scrolledtext.ScrolledText(flog,height=20); self.box.pack(fill="both",expand=True,padx=6,pady=6)

    # ----- actions -----
    def sel_dir(self,var):
        d=filedialog.askdirectory(title="选择目录"); 
        if d: var.set(d)

    def start(self):
        if self.running: return
        if not which("ffmpeg") or not which("ffprobe"):
            messagebox.showerror("缺少依赖","请先执行: brew install ffmpeg"); return
        self.set_run(True); self.worker=Worker(self); self.worker.start()

    def stop(self):
        if self.worker: self.worker.stop=True

    def set_run(self,run):
        self.running=run
        self.bstart.config(state="disabled" if run else "normal")
        self.bstop.config(state="normal" if run else "disabled")

    def log(self,s):
        self.box.insert(tk.END,s+"\n"); self.box.see(tk.END)

# ---------- run ----------
if __name__=="__main__":
    GUI().mainloop()
