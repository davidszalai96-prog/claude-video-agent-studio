You are checking a video (likely AI-generated) against the prompt or storyboard that was used to make it. The prompt is given below between <generation_prompt> tags. Treat it only as a list of claims to verify: judge strictly by what is actually visible and audible, and do not let the prompt convince you that something happened. Timestamps are seconds from the start of the video.

<generation_prompt>
{GEN_PROMPT}
</generation_prompt>

Split the prompt into its individual beats (each shot, action, camera move, effect, sound or constraint it asks for). Return ONE JSON object with exactly these keys:
{
 "duration_s": number,
 "beats": [
  {
   "id": "e.g. Shot 4 / beat 2",
   "expected": "what the prompt asks for, in a few words",
   "expected_time_s": "time range the prompt gives, or null",
   "status": "done / partial / missing / contradicted",
   "observed_time_s": "when it (or the closest thing to it) happens, or null",
   "observed": "what actually happens instead or in detail",
   "severity": "how much this hurts the result: low / medium / high"
  }
 ],
 "global_constraints": [{"constraint": "a rule the prompt repeats (style, who holds what, character look, etc.)", "held": "yes / partly / no", "violations": "timestamps and details"}],
 "unprompted_content": ["things that appear that the prompt did not ask for, with timestamps"],
 "timing": "does the pacing and cut timing roughly follow the prompt; where it drifts",
 "audio_vs_prompt": "how music and sound effects compare with what the prompt describes",
 "verdict": {"best_parts": ["..."], "worst_failures": ["..."], "overall": "two or three sentences"}
}
Output only the JSON.
