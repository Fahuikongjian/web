---
title: 让封面沿着滚动收进页眉
slug: css-scroll-flip-morph
date: 2026-11-20
category: 代码
tags: [CSS, 动效, 前端审美]
summary: 用 FLIP 测量封面和页眉之间的几何差，再把位移交给原生滚动进度。
cover: /static/images/cover-03.svg
featured: false
draft: false
---

我希望读者滑过星环手记的封面时，还能认出刚才那枚环。它从首屏的大图里缩进页眉，边缘的一点暖光跟着移动，标题在原处安静地让开。这段动效经得起正着滚，也经得起往回拖。滚到一半停手，构图也该站得住，像一张可以单独拿出来看的唱片封套。

## 先量两张静止的画面

FLIP 从起止两个矩形着手。把装饰图层放到页眉槽位，左上角作为缩放原点。读出首屏封面和槽位在同一坐标系里的位置，取两者左上角的差作为位移，再用宽高之比算出两个缩放值。图层先施加这组逆变换，看起来仍在首屏原位。两处画幅尽量一致，星环在途中就能保持圆润，图像裁剪则放到内层处理。

## 用滚动进度消去差值

滚动时只更新钳制在零到一之间的 `--cover-progress`。下面的横纵位移与缩放差由测量阶段写入，布局仍由原来的容器占位。进度增加时，逆变换逐渐归零，图层便回到页眉里的自然尺寸。

```css
.cover-art {
  --leftover: calc(1 - var(--cover-progress, 0));
  transform-origin: top left;
  transform:
    translate(calc(var(--dx, 0px) * var(--leftover)),
              calc(var(--dy, 0px) * var(--leftover)))
    scale(calc(1 + var(--scale-x-offset, 0) * var(--leftover)),
          calc(1 + var(--scale-y-offset, 0) * var(--leftover)));
}

@media (prefers-reduced-motion: reduce) {
  .cover-art { transform: none; }
}
```

> 调节奏时，我会先关掉光晕，单看星环在中途有没有挤进标题的阅读区。

## 在窄屏上重测

等字体就绪、窗口尺寸改变或横竖屏切换后，都重新测量起点和终点。普通滚动帧只写进度。为了排查跳动，我会从中段刷新，确认首帧就能还原当前滚动位置，再在窄屏上慢慢反向滚动。如果页眉标题换行，就再看一遍星环的落点与文字间距。开启减少动态效果时，装饰停在页眉槽位，首屏仍由静态构图撑住，读者照常抵达正文。
