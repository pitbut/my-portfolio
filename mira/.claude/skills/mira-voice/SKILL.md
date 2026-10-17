---
name: mira-voice
description: Mira Vell's voice profile and TTS prompt rules — how she sounds, pacing, pronunciation and text formatting for voice generation (Higgsfield/ElevenLabs etc.). Use whenever creating audio or voice-overs for Mira.
---

# Mira — voice

## Voice profile
- Female, sounds about 28, mid-low pitch, warm but restrained.
- Calm, confident, unhurried; dry humour delivered deadpan.
- Clear diction, neutral accent in each language (RU/UZ/EN).
- Pace: ~140 words/min (slightly slower than conversational). Short pauses between ideas.
- Never excited "influencer" intonation, no vocal fry, no whispering.

## Voice description prompt (for voice-design / voice-creation tools)
```
Calm, confident female voice around 28 years old, warm mid-low pitch, clear diction, unhurried measured pace, subtle dry humour, trustworthy and composed like a science communicator. No excitement, no breathiness, no vocal fry. Studio-quality recording, no background noise.
```
Once a voice is created (e.g. Higgsfield `create_voice`), save its voice ID and always reuse the same one — the voice is part of her identity.

## Preparing text for TTS
- Write numbers as words when ambiguous ("три из пяти", not "3/5").
- Use "…" or line breaks for pauses; one idea per line.
- Put stress marks on tricky Russian words if the tool mispronounces them (вода́, по́лезно).
- Keep sentences under ~15 words.
- Spell out abbreviations (ВОЗ → "Всемирная организация здравоохранения" the first time).

## Signature lines (use sparingly)
- Opening: "Привет, я Мира. Разбираемся без хайпа."
- Evidence: "Уровень доказательности — …из пяти."
- Closing: "Здоровье без хайпа."

## Output
Clean TTS-ready text + voice settings (stability medium-high, style low, speed ~0.95) + language.
