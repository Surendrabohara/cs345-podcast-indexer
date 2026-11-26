"""Part D: spoken summary with Azure neural text-to-speech."""
import base64

import azure.cognitiveservices.speech as speechsdk

from .config import require, settings

# Three voices with different personas (handout D3).
VOICES = {
    "en-US-JennyNeural": "Friendly",
    "en-US-GuyNeural": "Formal",
    "en-US-AriaNeural": "Energetic",
}
DEFAULT_VOICE = "en-US-JennyNeural"


def build_summary(episode_title: str, topics: list[str], sentiment: str, entities: list[dict]) -> str:
    """Plain-English summary: topic count and topics, sentiment, and entity types found."""
    shown = topics[:5]
    if shown:
        topic_text = f"{len(topics)} key topic{'s' if len(topics) != 1 else ''}: " + ", ".join(shown)
    else:
        topic_text = "no clear topics"
    counts: dict[str, int] = {}
    for e in entities:
        counts[e["category"]] = counts.get(e["category"], 0) + 1
    if counts:
        kinds = ", ".join(f"{n} {name.lower()}" for name, n in sorted(counts.items()))
        entity_text = f"I detected {kinds}."
    else:
        entity_text = "I did not detect any named entities."
    return f"{episode_title} mentions {topic_text}. The overall tone is {sentiment}. {entity_text}"


def synthesize(text: str, voice: str = DEFAULT_VOICE) -> dict:
    """Return the MP3 as base64 so the browser can play it with an <audio> element."""
    require("speech_key", "speech_region")
    if voice not in VOICES:
        voice = DEFAULT_VOICE
    config = speechsdk.SpeechConfig(subscription=settings.speech_key, region=settings.speech_region)
    config.speech_synthesis_voice_name = voice
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(f"Text-to-speech failed: {result.reason}")
    return {
        "audio_base64": base64.b64encode(result.audio_data).decode("ascii"),
        "audio_format": "mp3",
        "voice": voice,
        "char_count": len(text),
    }
