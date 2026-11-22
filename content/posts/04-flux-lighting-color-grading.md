---
title: 用 FLUX 做封面，先定光位再调色
slug: flux-lighting-color-grading
date: 2026-11-15
category: 图像生成
tags: [Flux, 光影, 色彩]
summary: 用一组单变量对照定下光位，再用灰度与缩略图检查午夜蓝和暖色反光。
cover: /static/images/starloop-cover.jpg
featured: false
draft: false
---

一张封面放在深色页面上，最容易丢掉的是深灰和蓝黑之间那点差别。我做黑胶星环时，会先确定边缘的光怎样掠过沟槽，再决定青光偏蓝多少。把颜色推得太早，眩光很容易盖住材质，缩成小图后只看得见一块发亮的蓝。

## 用一组对照找光位

做 FLUX 对照时，我会记录模型版本、种子和画幅，每轮只替换一句照明说明。先让左后方的主光沿沟槽擦过，再做一张高一点的版本。低位光通常留下细长的亮边，高位光更容易照亮盘面。把两张并排放，检查光带有没有顺着弧线变薄，以及内圈的暖色反射是否还留在原来的位置。

```yaml
baseline_prompt: >
  Matte vinyl ring on a midnight-blue backdrop, eye-level close-up.
  A narrow key light grazes the grooves from behind on the left.
  A faint amber reflection hugs the inner rim.
alternate_lighting: >
  A narrow key light grazes the grooves from higher up behind on the left.
```

> 对照图先看亮暗的分布。最亮的一小段，通常也是读者先看到的一小段。

## 把颜色留在该亮的位置

定下光位之后，我会临时切到灰度。若暗部在灰度下糊成一片，先轻抬阴影曲线，让内圈、盘面和背景分出层次。恢复颜色后，午夜蓝留在背景，青色沿受光边走，琥珀只占内缘一角。暖色反射一旦泛成白斑，就把它局部压暗一点，给色相和纹理腾出空间。

最后把成图放进深色页面，分别看原尺寸和小卡片。大图检查高光有没有吃掉沟槽，小图检查暗处是否还能勾出环形。我也会把卡片与它实际使用的背景色并排看，免得预览时的浅边框替暗部撑开了轮廓。标题旁如果冒出第二个视觉焦点，回看裁切和反光位置，再决定要重生成哪一处。[星环提示词](/articles/starloop-prompt-craft/)记录了这些光色在画幅里的摆位。
