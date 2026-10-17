---
name: mira-scene-still
description: Build photorealistic still-image prompts placing AI influencer Mira Vell into a scene (kitchen, gym, park, bedroom, etc.) and optionally generate them in Higgsfield. Use for any Mira photo/post/thumbnail request.
---

# Mira — scene still prompt

Depends on **mira-base-character** — copy its character block and outfit rules exactly.

## Inputs to collect (ask only what is missing)
1. Topic / post idea (e.g. "sleep hygiene", "morning walk").
2. Scene (use a library scene below or a new one).
3. Framing: full body / waist-up / chest-up portrait.
4. Aspect ratio: 4:5 (feed, default), 9:16 (stories/reels cover), 1:1, 3:2 (wide).

## Scene library (already generated as empty backgrounds)
- **Kitchen** — bright modern kitchen, light wood, vegetables, water pitcher, morning daylight → nutrition topics.
- **Studio** — minimalist yoga/fitness studio, oak floor, sage mat, plant, soft daylight → movement, posture, stretching.
- **Park** — morning park path, golden sunrise, haze, bench → walking, sunlight, mental health.
- **Bedroom** — calm evening bedroom, warm lamp, book, blue-hour window → sleep, recovery.
If the user has these background images in Higgsfield, attach the matching one as a second reference.

## Prompt template (English)
```
Photorealistic photo. [CHARACTER BLOCK from mira-base-character]
Outfit: [default or topic variation].
Scene: [scene description], [time of day and light].
Action: [one simple natural action — holding a glass of water, sitting on a mat, walking toward camera, etc.].
Framing: [full body / waist-up / chest-up], camera at eye level, [35mm scene / 85mm portrait] lens, shallow depth of field.
Expression: calm, serious, direct gaze [or: looking at the object].
Lighting consistent with the scene, natural shadows, person fully integrated into the environment, correct scale.
No text, no logos, no watermark.
```
Add the negative prompt from the base skill when supported.

## Higgsfield generation (if connected)
- Model: `nano_banana_pro` (≈2 credits, best at keeping the reference face). Premium option: `gpt_image_2_5`, quality high, 2k (≈2.75 credits).
- Attach Mira's master reference image (role `image_references`), plus the scene background if available.
- Always preflight with `get_cost: true` before the first generation in a session and tell the user the price.
- Basic plan allows only 2 parallel image jobs — submit batches of 2.

## Output to the user
1. The ready prompt in a code block.
2. One line: which references to attach.
3. Offer 2 variants (different action or framing) if useful.
