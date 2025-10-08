# 🎞️ SMB-Compatible Video Transcoder for macOS (GPU + GUI)

本工具用于在 macOS 上 **批量转码视频**，使其在 **iPad 或其他设备通过 SMB 网络播放** 时完全兼容。  
支持 **苹果 GPU 硬件加速 (VideoToolbox)**，带有 **图形界面 (Tkinter)** 和 **实时进度显示**。

---

## 🧩 功能特性

- ✅ **GPU 加速转码**：调用 macOS VideoToolbox（Intel / Apple Silicon 均支持）  
- ✅ **输出标准兼容格式**：H.264 + AAC + yuv420p + faststart（适合 SMB/iPad 播放）  
- ✅ **实时进度显示**：显示当前正在处理的视频与时间进度  
- ✅ **批量处理**：可递归扫描子目录  
- ✅ **安全覆盖**：可选“覆盖原文件”，自动临时文件保护机制  
- ✅ **图形界面操作**：无需命令行，直接点选目录、参数即可运行  

---

## ⚙️ 安装要求

### 1. 安装 Python 3
macOS 默认自带 Python 3，如无可执行：
```bash
brew install python
````

### 2. 安装 ffmpeg

```bash
brew install ffmpeg
```

---

## 🚀 使用步骤

1. 下载脚本

   ```bash
   git clone https://github.com/<yourname>/SMBTranscoder.git
   cd SMBTranscoder
   ```

2. 运行

   ```bash
   python3 SMBTranscodeGUI_Progress.py
   ```

3. 在图形界面中：

   * 选择 **输入目录**
   * 若想保留原视频 → 选择 **输出目录**
   * 若想直接替换 → 勾选 **覆盖原文件**（此时无需填写输出目录）
   * 调整参数：

     * **视频码率 (b:v)**：建议 5M（1080p），3M（720p）
     * **音频码率 (b:a)**：建议 128k（常规视频）
     * **采样率 (ar)**：建议 44100 Hz
   * 点击 “开始”
   * 日志框会实时显示当前视频与进度（如 `00:04:12`），并标记 ✅ 完成或 ❌ 失败。

---

## 📦 输出文件说明

* **默认模式**：输出到目标目录，文件名保持不变，扩展名 `.mp4`。
* **覆盖模式**：生成临时文件 `.tmp.smbfix.mp4`，成功后自动替换原文件。
* 输出视频结构：

  * 视频编码：`H.264 (yuv420p)`
  * 音频编码：`AAC`
  * 封装：`MP4`
  * 含 `+faststart`，优化 SMB / HTTP 流式播放。

---

## 🧠 参数建议

| 分辨率     | 视频码率   | 音频码率 | 采样率   | 说明        |
| :------ | :----- | :--- | :---- | :-------- |
| 720p    | 3M–4M  | 96k  | 44100 | 体积小，清晰度中等 |
| 1080p   | 5M     | 128k | 44100 | 推荐值       |
| 2K / 4K | 8M–12M | 192k | 48000 | 高画质或音乐类   |
| 仅语音     | 2M     | 64k  | 32000 | 节省空间      |

---

## 🧩 示例

命令行等效（单个文件）：

```bash
ffmpeg -hwaccel videotoolbox -i input.mp4 -c:v h264_videotoolbox -b:v 5M -pix_fmt yuv420p -c:a aac -b:a 128k -ar 44100 -movflags +faststart -y output.mp4
```

---

## 🪶 作者与许可证

**Author:** Guo
**License:** MIT
**Platform:** macOS (Intel / Apple Silicon)
**Last Update:** 2025-10-08

---

> 🧠 *本工具的核心目标是解决 iPad 通过 SMB 播放部分 MP4 文件时报错的问题。
> 转码后的视频均遵循 Apple AVFoundation 兼容标准，播放稳定、传输顺畅。*

```
```
