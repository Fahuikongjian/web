---
title: 星环封面的提示词从一束光开始
slug: starloop-prompt-craft
date: 2026-11-18
category: 图像生成
tags: [Prompt, 视觉, 色彩]
summary: 把黑胶、星环和午夜蓝写成可观察的摆位、材质和光源。
cover: /static/images/cover-02.svg
featured: true
draft: false
---

星环封面的想法来自唱片转到内圈时的反光。灯掠过沟槽，银线只亮半圈，剩下的部分融进暗处。我想把那一瞬做成封面，先写下物体怎么摆、光从哪里进来，以及哪块暗面留给标题。这样看到生成结果时，我也知道具体要改提示词里的哪一句。

## 先把构图摆出来

竖幅里只放一枚略偏右下的环，视角稍微倾斜，让外缘和内圈同时可见。把左上留给标题后，我会把提示词写成一段简短的拍摄说明。黑胶的沟槽承担近看的细节，封面缩成小卡片时，则靠那道断开的轮廓把环从深蓝背景里挑出来。

```yaml
prompt: >
  A single ring of matte black vinyl, slightly tilted in the lower-right
  of an upright composition. Thin grazing cyan light picks out its grooves.
  A small amber reflection touches the inner rim. Quiet midnight blue above
  and to the left, with sparse grain in the shadows.
aspect_ratio: "4:5"
```

## 给青色和琥珀分工

| 元素 | 画面中的位置 | 检查方式 |
| --- | --- | --- |
| 午夜蓝 | 左上留白与远处阴影 | 放上标题，看看边缘还有没有呼吸感 |
| 冷青 | 外缘受光侧与少量沟槽 | 缩成小图，确认弧线还能辨认 |
| 琥珀 | 内圈一小段反射 | 眯眼看，暖光应先于颗粒被看见 |

暗处还想留一点纸面的颗粒。颗粒一旦铺满高光，黑胶就容易显得像覆了一层砂。这时我会明确把颗粒放在阴影处，让受光的沟槽保持清楚。琥珀光若占了半个环，就缩小它在内缘的范围，让青线把视线带到那一点暖色上。

## 缩小以后再挑图

我会在同一排预览里保留原图和裁切图。先看环能否在缩略图里被一眼认出，再看标题区有没有突兀的亮斑。比较时固定画幅和主体位置，一轮只改光色或光线方向。构图失衡时，再单独挪环的位置。放进[图像页](/gallery/)之前，连同那版提示词一起保存，下一张封面就有了可以复用的起点。
