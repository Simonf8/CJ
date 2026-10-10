from __future__ import annotations

import math
import random
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw

KEY = (1, 2, 3)
MOUTH_Y = -0.39
COLORS = {
    "idle": (0, 229, 255),
    "listening": (130, 246, 255),
    "thinking": (255, 176, 32),
    "speaking": (0, 229, 255),
    "error": (255, 59, 92),
}


def _bump(x, y, cx, cy, sx, sy):
    return np.exp(-(((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2))


def build_head(rows: int = 46, cols: int = 104) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = np.repeat(np.linspace(1, -1, rows), cols)
    a = np.tile(np.linspace(0, 2 * np.pi, cols, endpoint=False), rows)
    rad = np.sqrt(np.clip(1 - y * y, 0, None))
    jaw = np.where(y < -0.2, 1 - 0.24 * np.power(np.clip((-0.2 - y) / 0.8, 0, None), 1.4), 1.0)
    crown = np.where(y > 0.6, 1 - 0.08 * (y - 0.6) / 0.4, 1.0)
    x = np.cos(a) * rad * 0.8 * jaw * crown
    z = np.sin(a) * rad * 0.86 * np.where(y < -0.15, 0.9 + 0.1 * jaw, 1.0)
    ax = np.abs(x)
    relief = (0.24 * _bump(x, y, 0, -0.06, 0.08, 0.2) + 0.09 * _bump(x, y, 0, -0.21, 0.13, 0.06)
              - 0.14 * _bump(ax, y, 0.29, 0.13, 0.12, 0.075) + 0.08 * _bump(ax, y, 0.29, 0.26, 0.2, 0.05)
              + 0.07 * _bump(ax, y, 0.43, -0.08, 0.15, 0.13) + 0.08 * _bump(x, y, 0, MOUTH_Y + 0.03, 0.19, 0.04)
              + 0.07 * _bump(x, y, 0, MOUTH_Y - 0.06, 0.17, 0.04) - 0.05 * _bump(x, y, 0, MOUTH_Y - 0.015, 0.2, 0.018)
              + 0.07 * _bump(x, y, 0, -0.72, 0.17, 0.1))
    front = np.clip(z / 0.5, 0, 1)
    z = np.where(z > 0, z + relief * front, z)
    detail = np.concatenate([np.clip(np.abs(relief) / 0.12, 0, 1) * front, np.zeros(440)])

    ny = np.repeat(-0.84 - np.arange(10) * 0.05, 44)
    na = np.tile(np.linspace(0, 2 * np.pi, 44, endpoint=False), 10)
    fade = np.concatenate([np.ones_like(x), np.repeat(1 - np.arange(10) / 10, 44)])
    pts = np.stack([np.concatenate([x, np.cos(na) * 0.32]),
                    np.concatenate([y, ny]),
                    np.concatenate([z, np.sin(na) * 0.3])], axis=1)
    lips = (pts[:, 2] > 0) & (np.abs(pts[:, 0]) < 0.24) & (np.abs(pts[:, 1] - MOUTH_Y) < 0.13)
    return pts, fade, lips, detail


class HologramRenderer:
    def __init__(self, width: int = 170, height: int = 210):
        self.w, self.h = width, height
        self.pts, self.fade, self.lips, self.detail = build_head()
        self.color = np.array(COLORS["idle"], dtype=np.float32)
        self.level = 0.0
        self.blink_at = 2.0

    def render(self, t: float, state: str = "idle", level: float = 0.0) -> Image.Image:
        target = np.array(COLORS.get(state, COLORS["idle"]), dtype=np.float32)
        self.color += (target - self.color) * 0.12
        self.level += (level - self.level) * (0.5 if level > self.level else 0.15)
        w, h = self.w, self.h
        unit = h * 0.3
        cx, top = w / 2, h * 0.4 + math.sin(t * 1.1) * h * 0.015

        thinking, listening = state == "thinking", state == "listening"
        yaw = math.sin(t * 0.9) * 0.12 + 0.18 if thinking else math.sin(t * 0.5) * 0.08 if listening else math.sin(t * 0.35) * 0.32
        pitch = 0.1 if thinking else -0.06 if listening else math.sin(t * 0.3) * 0.05
        mouth = self.level if state in ("speaking", "listening") else self.level * 0.3

        x, y, z = self.pts[:, 0], self.pts[:, 1].copy(), self.pts[:, 2]
        if mouth > 0.01:
            d = y - MOUTH_Y
            wgt = 1 - np.abs(x) / 0.24
            y = np.where(self.lips, y + np.where(d < 0, -mouth * 0.08 * wgt, mouth * 0.015 * wgt), y)
        cyw, syw, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        x1 = x * cyw + z * syw
        z1 = -x * syw + z * cyw
        y2 = y * cp - z1 * sp
        z2 = y * sp + z1 * cp
        persp = 3.2 / (3.2 - z2)
        px = (cx + x1 * unit * persp).astype(np.int32)
        py = (top - y2 * unit * persp).astype(np.int32)

        scan_period = 1.1 if thinking else 3.2
        scan_y = 1.1 - ((t % scan_period) / scan_period) * 2.6
        alpha = (0.06 + 0.6 * np.clip((z2 + 0.35) / 1.15, 0, 1) + 0.9 * self.detail) * self.fade
        alpha = np.where(np.abs(y - scan_y) < 0.05, np.minimum(1, alpha + 0.55), alpha)

        buf = np.zeros((h, w), dtype=np.float32)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            qx, qy = px + dx, py + dy
            ok = (qx >= 0) & (qx < w) & (qy >= 0) & (qy < h)
            np.add.at(buf, (qy[ok], qx[ok]), alpha[ok] * 0.42)

        self._beam(buf, cx, top + unit * 1.55, unit, t)
        intensity = np.clip(buf, 0, 1.6)
        rgb = np.empty((h, w, 3), dtype=np.float32)
        base = np.clip(intensity, 0, 1)[..., None] * self.color
        hot = np.clip(intensity - 1, 0, 0.6)[..., None] / 0.6 * (255 - self.color)
        rgb[:] = base + hot
        rgb[intensity < 0.16] = KEY
        img = Image.fromarray(rgb.astype(np.uint8), "RGB")
        self._eyes(img, cx, top, unit, (cyw, syw, cp, sp), t, state)
        return img

    def _beam(self, buf: np.ndarray, cx: float, base_y: float, unit: float, t: float) -> None:
        h, w = buf.shape
        yy, xx = np.mgrid[0:h, 0:w]
        ring = np.abs(((xx - cx) / (unit * 0.42)) ** 2 + ((yy - base_y) / (unit * 0.1)) ** 2 - 1) < 0.25
        buf[ring] += 0.9
        for i in range(14):
            p = (t * 0.25 + i / 14) % 1
            mx = int(cx + math.sin(i * 7.3) * unit * (0.25 + p * 0.5))
            my = int(base_y - p * unit * 1.6)
            if 0 <= mx < w - 1 and 0 <= my < h - 1:
                buf[my:my + 2, mx:mx + 2] += 0.9 * (1 - p)

    def _eyes(self, img: Image.Image, cx, top, unit, rot, t, state) -> None:
        if t > self.blink_at + 0.16:
            self.blink_at = t + 2.5 + random.random() * 4
        blink = abs(math.sin((t - self.blink_at) / 0.16 * math.pi)) if t > self.blink_at else 0
        cyw, syw, cp, sp = rot
        glow = 1.0 if state == "listening" else 0.85 if state == "thinking" else 0.7 + self.level * 0.3
        c = tuple(int(v + (255 - v) * 0.7 * glow) for v in self.color)
        draw = ImageDraw.Draw(img)
        for ex, ey, ez in ((-0.29, 0.13, 0.7), (0.29, 0.13, 0.7)):
            x1 = ex * cyw + ez * syw
            z1 = -ex * syw + ez * cyw
            y2 = ey * cp - z1 * sp
            z2 = ey * sp + z1 * cp
            persp = 3.2 / (3.2 - z2)
            px, py = cx + x1 * unit * persp, top - y2 * unit * persp
            rw, rh = unit * 0.07, max(0.8, unit * 0.03 * (1 - blink * 0.9))
            draw.ellipse([px - rw, py - rh, px + rw, py + rh], fill=c)
