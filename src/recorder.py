"""Enregistrement de l'écran avec ffmpeg, partagé par demo.py et go.py."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import time
from pathlib import Path


def find_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    pattern = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe")
    return next(iter(glob.glob(pattern)), None)


class Recorder:
    """Filme tout le bureau (gdigrab) en .mkv (lisible même si le programme plante), remuxé en .mp4 à l'arrêt."""

    def __init__(self, ffmpeg: str, out_mp4: Path, fps: int) -> None:
        self.ffmpeg, self.mp4, self.mkv, self.fps = ffmpeg, out_mp4, out_mp4.with_suffix(".mkv"), fps
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "gdigrab", "-framerate", str(self.fps),
               "-draw_mouse", "1", "-i", "desktop", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
               "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", str(self.mkv)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(2)
        if self.proc.poll() is not None:
            raise RuntimeError("ffmpeg n'a pas démarré : " + self.proc.stderr.read().decode("utf-8", "replace")[-300:])

    def stop(self) -> Path | None:
        if not self.proc:
            return None
        try:
            self.proc.stdin.write(b"q")
            self.proc.stdin.flush()
            self.proc.wait(timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()
        self.proc = None
        if not self.mkv.exists():
            return None
        done = subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(self.mkv), "-c", "copy",
                               "-movflags", "+faststart", str(self.mp4)], capture_output=True)
        if done.returncode == 0 and self.mp4.exists():
            self.mkv.unlink(missing_ok=True)
            return self.mp4
        return self.mkv


class PausableRecorder:
    """Vidéo avec pauses (une connexion à un site ne doit pas être filmée) : un morceau par reprise, recollés à la fin."""

    def __init__(self, ffmpeg: str, out_mp4: Path, fps: int) -> None:
        self.ffmpeg, self.out, self.fps = ffmpeg, out_mp4, fps
        self.current: Recorder | None = None
        self.parts: list[Path] = []

    def start(self) -> None:
        if self.current is None:
            self.current = Recorder(self.ffmpeg, self.out.with_name(f"{self.out.stem}_{len(self.parts)}.mp4"), self.fps)
            self.current.start()

    def pause(self) -> None:
        if self.current is not None:
            part = self.current.stop()
            self.current = None
            if part:
                self.parts.append(part)

    def finish(self) -> Path | None:
        self.pause()
        if not self.parts:
            return None
        if len(self.parts) == 1:
            return self.parts[0].replace(self.out.with_suffix(self.parts[0].suffix))
        listing = self.out.with_suffix(".txt")
        listing.write_text("".join(f"file '{p.name}'\n" for p in self.parts), encoding="utf-8")
        done = subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                               "-c", "copy", "-movflags", "+faststart", str(self.out)], capture_output=True)
        if done.returncode != 0 or not self.out.exists():
            return self.parts[0]  # morceaux laissés sur le disque
        listing.unlink(missing_ok=True)
        for part in self.parts:
            part.unlink(missing_ok=True)
        return self.out
