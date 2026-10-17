---
name: mira-content-engine
description: Content strategy engine for AI health influencer Mira Vell — generates post/reel ideas, weekly and monthly content plans, captions and hashtags, and routes each item to the right Mira production skill. Use for "ideas", "content plan", "caption", "what to post".
---

# Mira — content engine

Uses **mira-base-character** for voice and rules. Routes production to **mira-scene-still**, **mira-silent-scene**, **mira-talking-scene**, **mira-voice**.

## Content pillars (rotate)
1. **Миф или факт за 30 секунд** — debunk a viral health claim, with evidence score. (talking scene)
2. **Сон** — sleep hygiene, routines. (bedroom)
3. **Питание без диет** — simple food habits, water, fiber. No calorie numbers or weight-loss targets. (kitchen)
4. **Движение** — walking, posture, stretching for desk workers. (studio / park)
5. **Разбор вирусного совета** — react to a trend, score its evidence. (talking scene)
6. **7-дневный челлендж** — one small habit per day. (series)

## Formats
- Reel/TikTok talking head 15–45 s — main format (3×/week).
- Silent b-roll reel with text overlay 7–10 s (2×/week).
- Carousel 5–7 slides: cover still + text slides (1×/week).
- Story: poll "миф или факт?" (daily optional).

## For each idea output
| Field | Content |
|---|---|
| Pillar | … |
| Hook (first 3 s) | … |
| Key message | 1 sentence |
| Evidence score | 1–5 + source to verify (never invent sources; mark "проверить") |
| Format + scene | e.g. talking scene / kitchen |
| Production skill | which Mira skill to run next |
| Caption | 2–4 short lines + CTA ("Сохрани", "Отправь другу") |
| Hashtags | 5–8, mix of broad and niche |

## Weekly plan default
Mon myth-buster · Tue silent b-roll · Wed talking tip · Thu carousel · Fri viral-advice review · Sat silent b-roll · Sun challenge recap.

## Rules
- Every health claim must be general, mainstream and checkable; flag anything the user must verify.
- No diagnoses, dosages, supplement or detox promotion, no body-shaming, no weight-loss numbers.
- Sponsored posts: label "Реклама/Sponsored" on screen and in caption.
- Mira is openly AI — include "AI" in bio and disclose in captions where platforms require it.

## Output
A table plan (week or month) in chat; offer to turn it into a spreadsheet/tracker if the user wants to keep it.
