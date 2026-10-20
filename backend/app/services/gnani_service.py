import os
import io
import base64
import tempfile
from typing import Optional, Tuple
from backend.app.providers.gnani_stt import GnaniSTTProvider
from backend.app.providers.gnani_tts import GnaniTTSProvider


class GnaniService:
    """
    Unified enterprise service wrapper for Gnani STT (Prisma) and TTS (Timbre)
    supporting Indic regional languages and Indian English.
    """

    SUPPORTED_LANGUAGES = {
        "hi-IN": "Hindi (हिंदी)",
        "en-IN": "Indian English",
        "ta-IN": "Tamil (தமிழ்)",
        "te-IN": "Telugu (తెలుగు)",
        "kn-IN": "Kannada (ಕನ್ನಡ)",
        "ml-IN": "Malayalam (മലയാളം)",
        "mr-IN": "Marathi (मराठी)",
        "bn-IN": "Bengali (বাংলা)",
        "gu-IN": "Gujarati (ગુજરાતી)",
        "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GNANI_API_KEY")
        self.stt_provider = GnaniSTTProvider(api_key=self.api_key)
        self.tts_provider = GnaniTTSProvider(api_key=self.api_key)

    def transcribe_file(
        self,
        audio_path: str,
        language_code: str = "hi-IN",
        bias_words: Optional[list] = None,
    ) -> Optional[str]:
        """
        Transcribe an audio file using Gnani STT with automatic mono/16kHz normalization.
        """
        if not os.path.exists(audio_path):
            return None

        # Primary transcription attempt
        transcript = self.stt_provider.transcribe(
            audio_path,
            language_code=language_code,
            native_numerals=(language_code == "hi-IN"),
            bias_words=bias_words,
        )

        # Fallback between hi-IN and en-IN for bilingual Indian retail utterances
        if (transcript is None or not transcript.strip()) and language_code in ("hi-IN", "en-IN"):
            alt_lang = "en-IN" if language_code == "hi-IN" else "hi-IN"
            alt_transcript = self.stt_provider.transcribe(
                audio_path,
                language_code=alt_lang,
                native_numerals=(alt_lang == "hi-IN"),
                bias_words=bias_words,
            )
            if alt_transcript and alt_transcript.strip():
                return alt_transcript.strip()

        return transcript.strip() if transcript else (transcript or "")

    def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        language_code: str = "hi-IN",
        format_ext: str = ".wav",
        bias_words: Optional[list] = None,
    ) -> Optional[str]:
        """
        Write audio bytes to a temporary WAV container and transcribe via Gnani STT.
        """
        if not audio_bytes:
            return ""

        temp_file = tempfile.NamedTemporaryFile(suffix=format_ext, delete=False)
        temp_path = temp_file.name
        temp_file.close()

        try:
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            return self.transcribe_file(temp_path, language_code=language_code, bias_words=bias_words)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def synthesize_speech(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice: Optional[str] = None,
    ) -> Tuple[Optional[bytes], str]:
        """
        Synthesize text into WAV audio bytes using Gnani Timbre TTS.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return None, "audio/wav"

        try:
            audio_bytes, content_type = self.tts_provider.synthesize(
                clean_text,
                language_code=language_code,
                voice=voice,
            )
            return audio_bytes, content_type
        except Exception as e:
            print(f"GnaniService TTS synthesis warning: {e}")
            return None, "audio/wav"

    def synthesize_speech_base64(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convenience helper to return base64 encoded audio for WebSocket and JSON payloads.
        """
        audio_bytes, _ = self.synthesize_speech(text, language_code=language_code, voice=voice)
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8")
        return None

