You are reviewing a video that may be AI-generated. Describe ONLY what is actually visible and audible. Do not guess at a story or at what the creator intended; if something is unclear, say so. Timestamps are seconds from the start of the video; be as precise as you can.

Return ONE JSON object with exactly these keys:
{
 "duration_s": number,
 "overall_style": {"medium": "2D hand-drawn / 2D digital / 3D CG / live-action / mixed", "notes": "line art, shading, lighting, backgrounds; any moments where the look changes"},
 "shots": [
  {
   "index": 1,
   "start_s": 0.0, "end_s": 0.0,
   "transition_in": "how this shot begins: hard cut, match cut (on what shape/object/action), continuous, dissolve, flash",
   "framing": "shot size and angle: overhead, low, eye level, wide, medium, close-up; level or canted",
   "camera_motion": "every camera move with timestamps: pan, tilt, zoom in/out, push/pull, tracking, arc, roll, shake, whip, or static",
   "action": "what happens, in order, with timestamps; say who or what moves and how",
   "subjects_state": "for each character: visible?, pose, on the ground / floating / falling / other, where the feet are",
   "contact_and_holding": "what holds or touches what (hands, hair, tails, tools, weapons); anything floating unsupported",
   "secondary_motion": "hair, cloth, smoke: separate strands or one solid mass; blown/floating or hanging with gravity; follow-through after movement",
   "effects": "particles, smoke, fire, debris, sparks, ash, speed lines, smears, impact flashes, light flares; how dense",
   "idle_spans": "any stretch over ~0.4 s where little or nothing moves, with timestamps",
   "physics": "is weight, momentum and impact believable; where not",
   "artifacts": "morphing, melting, identity or costume drift, extra or missing limbs, flicker, garbled text, sudden jumps"
  }
 ],
 "notable_events": [{"time_s": 0.0, "event": "short description"}],
 "consistency": "do characters, costumes, props and locations stay consistent; list changes with timestamps",
 "audio": {"music": "instruments, tempo, dynamics and where they change", "sound_effects": "which sounds occur and whether they line up with the visible action (timestamps)", "voices": "speech or singing, or none"},
 "strongest_moments": ["timestamp and why"],
 "biggest_problems": ["timestamp and why"]
}
Output only the JSON.
