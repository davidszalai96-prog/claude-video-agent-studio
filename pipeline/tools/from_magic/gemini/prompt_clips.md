You are helping a music-video editor choose shots from AI-generated fantasy animation clips. The clips have no story; the editor needs an accurate visual inventory.

For the video, describe every shot (a shot ends at a hard cut; a continuous camera move is one shot). Describe only what you see. Timestamps are seconds from the start of the video, two decimals.

Schema:
{
  "shots": [
    {
      "start_s": 0.00,
      "end_s": 0.00,
      "character": "who is on screen: type/species, apparent gender, hair colour and style, outfit, dominant colours, props or creatures; 'none' if no character",
      "framing": "extreme close-up | close-up | medium | wide | extreme wide",
      "action": "one sentence: what happens in the shot",
      "action_type": "impact | strike | spin | rise | transform | sweep | fly | pose | other",
      "motion_intensity": 1,
      "camera": "static | push in | pull out | pan left | pan right | tilt up | tilt down | orbit | tracking | other",
      "key_moments": [{"t": 0.00, "what": "e.g. strike lands, flash, burst of energy, wings open, head turn"}],
      "best_moment_s": 0.00,
      "artifacts": [{"t": 0.00, "what": "visible AI glitch such as morphing hands, distorted face, flicker, melting, garbled text"}],
      "dominant_colors": ["..."],
      "brightness": "dark | medium | bright"
    }
  ],
  "visible_text_or_logos": "none, or what and where"
}

motion_intensity: 1 = almost still, 3 = moderate movement, 5 = very fast or violent movement (subject and camera combined).
