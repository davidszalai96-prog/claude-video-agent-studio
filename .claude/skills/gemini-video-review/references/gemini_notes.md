# Gemini notes for video review

## Measured on the user's free-tier key (September 2026)

These numbers were measured by the user and may change. Check `--list-models` and the error text if something stops working.

- **Limits:**
  - 5 requests per minute.
  - **20 requests per day**, which makes requests the scarce resource.
  - 250k tokens per minute.
- **Batching:** one request can carry up to 10 videos and still counts as one request. Prefer `--batch` when reviewing several clips.
  - Batches must also fit the per-minute token budget. Ten 15 s clips at 12 fps come to about 470k tokens, which is over it. For big batches, lower the fps (6, or 2–3 for semantics only) or use `--low-res`.
- **Token cost:** a 15 s H3 clip at 6 fps used about 25k tokens.
- **HTTP 503 "high demand":** this is Gemini running out of capacity, not your quota. It once lasted over 1.5 hours.
  - Back off 10 minutes or more, then retry the same request.
  - Don't split a batch into more requests because of a 503; that only burns the daily budget.
- **Models:**
  - `gemini-3.8-flash` works and is the default.
  - `gemini-2.5-flash` returns 404 on this free tier.
  - `gemini-omni-*` models have a limit of 0.
  - Use `--model NAME` to switch, and `--list-models` to see what the key can use.

## Accuracy of Gemini's descriptions

- **Timestamps:** treat them as ±0.25 s. In one measurement they ran 0–208 ms early (median about 140 ms, 3–4 frames at 24 fps). For exact cut times use `frames.py --cuts` and the contact sheets.
- **Left and right:** Gemini has reversed screen direction in a tracking shot before. Verify direction on the frames.
- **Leading questions:** Gemini tends to confirm what the prompt says should happen. Hence blind `shots` mode first, and neutral wording in `--extra`.
- **Counting and fine detail:** it may miss single-frame events at low fps. Impact frames and smears usually last 1–3 frames, so use 12 fps or higher for anime action, and check the frames yourself.

## How the script sends video

- **Inline:** videos go inline (base64) while the raw total per request stays under 45 MB, which you can change with `GEMINI_INLINE_LIMIT`.
- **Files API:** larger videos are uploaded through the Files API. The script waits until each file is ACTIVE and deletes it afterwards.
- **Sampling options:** `videoMetadata.fps` sets the sampling rate. `startOffset`/`endOffset` come from `--start`/`--end`.
- **Low resolution:** `--low-res` sets `mediaResolution` to `MEDIA_RESOLUTION_LOW`, about 66 tokens per frame instead of about 258. If a model rejects it (HTTP 400), drop the flag.
- **Key handling:** the key travels only in the `x-goog-api-key` header, never in a URL. Error text is scrubbed of it before being logged or saved.

## Error table

| HTTP / message | Meaning | What to do |
|---|---|---|
| 400 `API_KEY_INVALID` | Wrong or revoked key | Ask the user to check the key file or variable. Never ask them to paste it. |
| 400 other | An option the model doesn't accept, or a bad video | Retry without `--low-res`, offsets or an unusual fps; try another model. |
| 403 | The key has no access to this API | The user should check the key's project in Google AI Studio. |
| 404 | Unknown model | Run `--list-models` and pick one that supports generateContent. |
| 413 | Request too large | Lower `GEMINI_INLINE_LIMIT` so the video goes through the Files API. |
| 429 | Rate or daily limit | Wait for the next minute or the next day; batch future requests. |
| 500 / 503 | Server error or capacity | The script already retried twice; wait 10+ minutes. |
| Network error | Sandbox blocks the domain | Allow `generativelanguage.googleapis.com` in network settings. |
| `finish_reason` = `MAX_TOKENS` | The answer was cut off | Rerun with `--max-output-tokens 32768`, fewer videos per batch, or a narrower segment. |
| `finish_reason` = `SAFETY` / empty | The response was blocked | Check `prompt_feedback` in the report. Rephrase custom prompts or analyze a shorter segment. |
