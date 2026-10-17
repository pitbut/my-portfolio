---
name: mira-talking-scene
description: "Create talking-to-camera videos of AI influencer Mira Vell — script (15–60 s), shot prompt and voice/lip-sync setup. Use when Mira must speak: tips, myth-busting, evidence-score explainers."
---

# Mira — talking scene (speaks to camera)

Depends on **mira-base-character** (look) and **mira-voice** (voice). Start from an approved chest-up or waist-up still.

## Inputs
1. Topic and the one claim/tip.
2. Evidence score 1–5 and the source (if the user doesn't know — say so and suggest checking; never invent a study).
3. Length: 15 s (≈40 words), 30 s (≈80 words), 60 s (≈150 words).
4. Language: RU / UZ / EN.

## Script structure
1. **Hook (0–3 s)**: myth or question. "Нужно ли пить 8 стаканов воды в день?"
2. **Answer**: plain language, 1–3 short sentences.
3. **Evidence score**: "Уровень доказательности: 3 из 5" + what that means.
4. **Practical takeaway**: one thing to do today.
5. **Sign-off**: "Здоровье без хайпа. Я — Мира." For medical topics add: "Если есть симптомы — к врачу, не ко мне."
Rules: short sentences, no jargon, no diagnoses or dosages, no product promotion; mark sponsorship on screen if any.

## Shot prompt (English, for the video model)
```
Mira from the reference image, same face and outfit, consistent identity, chest-up framing, facing camera, eye level.
She speaks calmly and clearly to the camera, natural lip movement synced to speech, small natural head movements, occasional blink, calm serious expression with a slight warmth.
Background: [scene], soft light, shallow depth of field. Static camera or very slow push-in.
Photorealistic, real skin texture, no morphing, no text on screen.
```

## Production flow
1. Write script → show to user for approval.
2. Generate voice track with **mira-voice**.
3. Lip-sync the still/clip to the audio in Higgsfield (talking-avatar / lip-sync model; check `models_explore` and `get_cost` first).
4. Captions: add burned-in subtitles in editing (CapCut etc.) — evidence score as a small on-screen badge "📊 3/5".

## Output
Script (with timing), shot prompt in a code block, list of on-screen text overlays.
