import io
import os
import wave
import requests


def _pcm_to_wav(pcm_bytes, sample_rate=48000, num_channels=1, sampwidth=2):
    """
    Ensures audio bytes are wrapped in a standard RIFF/WAV container.
    Gnani Timbre API often returns raw PCM stream without a RIFF header.
    Browsers require a standard RIFF header to decode and play audio.
    """
    if pcm_bytes.startswith(b"RIFF"):
        return pcm_bytes
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


class GnaniTTSProvider:
    """
    Adapter for Gnani Timbre Text-to-Speech API (Vachana platform).

    Endpoint:
        POST https://api.vachana.ai/api/v1/tts/inference

    Authentication: X-API-Key-ID header.

    Supported Languages:
        Hindi, English, Tamil, Telugu, Kannada, Malayalam, Marathi,
        Bengali, Punjabi, Gujarati.
    """

    DEFAULT_ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"
    DEFAULT_MODEL = "timbre-v3.0"
    DEFAULT_VOICE = "Shivani"

    def __init__(self, api_key=None, endpoint=None):
        self.api_key = api_key or os.getenv("GNANI_TTS_API_KEY") or os.getenv("GNANI_API_KEY")
        self.endpoint = endpoint or os.getenv("GNANI_TTS_ENDPOINT", self.DEFAULT_ENDPOINT)

    def synthesize(self, text, language_code="hi-IN", voice=None, sample_rate=48000):
        """
        Synthesizes text into spoken audio bytes containerized as valid WAV.

        Returns:
            (audio_bytes: bytes, content_type: str)
        """
        if not self.api_key:
            raise RuntimeError("GNANI_API_KEY or GNANI_TTS_API_KEY is not configured.")

        model = os.getenv("GNANI_TTS_MODEL", self.DEFAULT_MODEL)
        voice_name = voice or os.getenv("GNANI_TTS_VOICE", self.DEFAULT_VOICE)

        headers = {
            "X-API-Key-ID": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "voice": voice_name,
            "model": model,
            "language_code": language_code,  # Gnani Timbre is multilingual; this ensures correct pronunciation
        }

        try:
            response = requests.post(self.endpoint, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                # Wrap in standard WAV container so browser can decode and play immediately
                wav_bytes = _pcm_to_wav(response.content, sample_rate=sample_rate)
                return wav_bytes, "audio/wav"
            else:
                raise RuntimeError(
                    f"Gnani TTS returned HTTP {response.status_code}: {response.text[:300]}"
                )
        except requests.RequestException as e:
            raise RuntimeError(f"Gnani TTS connection failure: {e}")
