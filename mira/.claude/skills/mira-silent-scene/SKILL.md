---
name: mira-silent-scene
description: Write image-to-video prompts for short silent clips of AI influencer Mira Vell (no speech — b-roll, reels backgrounds, transitions) for Seedance/Kling in Higgsfield. Use when the user wants Mira moving without talking.
---

# Mira — silent scene (video without speech)

Depends on **mira-base-character**. A silent scene always starts from an approved still (make it with **mira-scene-still** first) — image-to-video keeps the face far better than text-to-video.

## Inputs
1. Start image (approved Mira still).
2. What happens (one action).
3. Duration: 5 s default (max 10 s). Format 9:16 for reels/TikTok unless told otherwise.
4. Mood: calm / energetic / cozy.

## Rules for good motion
- ONE main action per clip, slow and natural. No complex choreography.
- Describe camera separately from the subject.
- Keep her face visible and turned toward camera at least half the clip.
- No lip movement / no talking (it is a silent clip): "mouth closed, not speaking".
- Hands: simple actions only (holding a glass, placing a mat, turning a page).

## Prompt template (English)
```
Mira from the reference image, same face and outfit, consistent identity.
Action: [single slow natural action].
Camera: [static / slow push-in / slow pan left / handheld subtle sway].
Mood and light: [calm morning daylight / warm evening lamp], light stays consistent with the start frame.
Mouth closed, not speaking, calm serious expression, natural blinking and breathing.
Photorealistic, real skin texture, smooth natural motion, no morphing, no extra people, no text.
```

## Ready-made actions by scene
- Kitchen: pours water into a glass and takes a sip; slices a cucumber on the board.
- Studio: rolls out the sage mat and sits cross-legged; slow side stretch.
- Park: walks toward camera along the path, sun behind her; sits down on the bench.
- Bedroom: switches off the lamp; closes the book and puts it on the nightstand.

## Higgsfield generation (if connected)
- Basic plan: Seedance 2.0 Fast / 2.0 Mini (≈17 credits per clip on Basic — check with `get_cost: true` first and tell the user).
- Pass the start still as the image input; 5 s, 9:16.
- Generate one clip, show it, then iterate — video is the most expensive item.

## Output
Prompt in a code block + chosen duration/format + credit estimate.
