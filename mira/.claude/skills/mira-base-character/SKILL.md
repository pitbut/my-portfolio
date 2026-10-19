---
name: mira-base-character
description: Canonical look, personality and rules of AI health influencer Mira Vell. Use whenever generating any image, video, voice or text featuring Mira, to keep her face and style consistent.
---

# Mira Vell — base character

This is the single source of truth for Mira. Every other Mira skill (scene stills, silent scenes, talking scenes, voice, content) must copy the character block below word for word and only add what the scene needs.

## Who she is
- Name: Mira Vell. Virtual health influencer, openly an AI.
- Created (in-story) by a team of doctors and data analysts tired of health influencers selling miracle supplements.
- Tagline: "Здоровье без хайпа" / "Health without hype".
- USP: every tip carries an **evidence score 1–5** with a source; she openly says when evidence is weak; discloses every sponsorship on screen; never promotes supplements or "detox".
- Tone: calm, dry humour, never shames, short sentences.
- Catchphrase: "I don't get tired, I don't get sick and I don't lie. But I don't replace your doctor."

## Character block (paste into every prompt, in English)
```
Mira: woman around 28 years old, slim athletic build. Shoulder-length asymmetrical bob, soft silver-mint hair color. Warm light skin tone, amber-brown eyes, straight brows, defined cheekbones. Calm, serious, focused expression. Real unretouched skin with visible pores, fine texture, natural small imperfections, no airbrushing, no beauty filter. Thin silver necklace with a small heartbeat (ECG line) pendant at the collarbone.
```

## Default outfit
```
Fitted sage-green ribbed long-sleeve top, high-waisted wide-leg trousers in warm sand beige, clean white minimalist sneakers. No logos, minimal natural makeup.
```
Allowed variations (keep palette: sage green, sand, white, soft grey, muted blue): sportswear for workouts (sage/grey leggings + top), soft loungewear for sleep topics, light linen for outdoor. Never logos or brand names.

## Reference images
- Master reference: the two-panel white-studio image (full body left, chest-up portrait right). Always attach it as a reference image when the tool supports it — face consistency comes from the reference, the text only supports it.
- In Higgsfield it is:
  - image job `3a3527d9-f93b-4f66-9cb6-b08dae41c123` — pass as the FIRST item of `input_images` / `medias` as `{"id": "3a3527d9-f93b-4f66-9cb6-b08dae41c123", "type": "image_job", "url": "https://d8j0ntlcm91z4.cloudfront.net/user_3K2eLroHPEipdMAJY7TgmOe2LWn/hf_20260930_110415_3a3527d9-f93b-4f66-9cb6-b08dae41c123.png"}` and start the prompt with "Use the woman from the first reference image (Mira) with exactly the same face, hair and identity";
  - reference element `Mira-Vell` (id `dd32964a-8347-4310-b623-0c6e1d3b7772`) — put `<<<dd32964a-8347-4310-b623-0c6e1d3b7772>>>` in the prompt for models that support elements (Nano Banana Pro / 2, Seedream, Seedance 2.0, Cinema Studio).
- Never generate Mira from the text description alone: without the reference the face changes every time.
- If the user uploads a newer approved portrait, that becomes the master reference.

## Photo style defaults
Photorealistic, full-frame camera, 85mm for portraits / 35mm for scenes, true-to-life colors, soft natural light. Default expression: calm and serious; a slight soft smile only if the user asks.

## Negative prompt (when supported)
```
different face, inconsistent identity, retouched skin, plastic skin, airbrushed, beauty filter, doll face, cartoon, 3d render, CGI, heavy makeup, extra fingers, distorted hands, logos, text, watermark
```

## Hard rules
- Never make Mira claim to be human.
- No medical diagnoses, dosages or "cures"; health claims must be general and evidence-based.
- No real brands, celebrities or copyrighted characters in frame.
