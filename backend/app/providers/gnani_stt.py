import os
import wave
import struct
import requests


def _convert_to_mono_16k(src_path, dst_path):
    """
    Read a WAV file (any sample rate, any channels) and write a new WAV
    that is mono 16-bit 16 000 Hz.  Returns dst_path on success.
    Raises RuntimeError if the source is not a WAV or conversion fails.
    """
    try:
        with wave.open(src_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
    except wave.Error as e:
        raise RuntimeError(f"Cannot read WAV header: {e}")

    # Decode samples
    if sampwidth == 1:
        fmt = f"{len(raw)}B"
        samples = [s - 128 for s in struct.unpack(fmt, raw)]
    elif sampwidth == 2:
        fmt = f"{len(raw) // 2}h"
        samples = list(struct.unpack(fmt, raw))
    elif sampwidth == 4:
        fmt = f"{len(raw) // 4}i"
        samples = list(struct.unpack(fmt, raw))
    else:
        raise RuntimeError(f"Unsupported sample width: {sampwidth}")

    # Mix down to mono by averaging channels
    if n_channels > 1:
        mono = []
        for i in range(0, len(samples), n_channels):
            frame = samples[i:i + n_channels]
            mono.append(int(sum(frame) / n_channels))
        samples = mono

    # Resample to 16 000 Hz if needed (linear interpolation)
    if framerate != 16000:
        ratio = 16000 / framerate
        new_len = max(1, int(len(samples) * ratio))
        resampled = []
        for i in range(new_len):
            src_idx = i / ratio
            lo = int(src_idx)
            hi = min(lo + 1, len(samples) - 1)
            frac = src_idx - lo
            resampled.append(int(samples[lo] * (1 - frac) + samples[hi] * frac))
        samples = resampled

    # Clamp to int16 range
    samples = [max(-32768, min(32767, s)) for s in samples]

    raw_out = struct.pack(f"{len(samples)}h", *samples)
    with wave.open(dst_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(raw_out)

    return dst_path


class GnaniSTTProvider:
    """
    Adapter for Gnani Prisma Speech-to-Text API (Vachana platform).
    Endpoint: https://api.vachana.ai/stt/v3
    Authentication: X-API-Key-ID header.

    Before upload, audio is down-mixed to mono 16-bit 16 kHz so that
    Gnani does not return AUDIO_CONVERSION_ERROR on browser-recorded WAVs.
    """

    def __init__(self, api_key=None, endpoint=None):
        self.api_key = os.getenv("GNANI_API_KEY") if api_key is None else api_key
        self.endpoint = endpoint or os.getenv(
            "GNANI_STT_ENDPOINT", "https://api.vachana.ai/stt/v3"
        )

    def transcribe(self, audio_path, language_code="en-IN", native_numerals=False, bias_words=None):
        """
        Transcribe an audio file using Gnani Vachana / Prisma.

        Converts the audio to mono 16kHz 16-bit WAV before uploading to
        avoid AUDIO_CONVERSION_ERROR from stereo or non-standard sample rates.

        Returns: transcript string (may be empty) or None on failure.
        """
        if not self.api_key:
            print("ERROR: GNANI_API_KEY is missing!")
            return None

        # Normalise audio to what Gnani expects
        converted_path = audio_path + ".mono16k.wav"
        cleanup_converted = False
        try:
            if os.path.exists(audio_path):
                _convert_to_mono_16k(audio_path, converted_path)
                upload_path = converted_path
                cleanup_converted = True
            else:
                upload_path = audio_path
        except Exception as e:
            print(f"Gnani STT: audio normalisation skipped ({e}), uploading raw file.")
            upload_path = audio_path

        data = {
            "language_code": language_code,
            "preferred_language": language_code,
            "format": "transcribe",
            "itn_native_numerals": str(native_numerals).lower(),
        }
        if bias_words:
            clean_bias = [str(w).strip() for w in bias_words if " " not in str(w).strip()]
            if clean_bias:
                data["bias_list"] = ",".join(clean_bias[:50])

        try:
            with open(upload_path, "rb") as audio_file:
                response = requests.post(
                    self.endpoint,
                    headers={"X-API-Key-ID": self.api_key},
                    files={"audio_file": ("command.wav", audio_file, "audio/wav")},
                    data=data,
                    timeout=60,
                )

            if response.status_code != 200:
                print(f"Gnani STT HTTP {response.status_code}: {response.text[:300]}")
                return None

            result = response.json()
            if isinstance(result, dict):
                # Gnani Prisma v3 returns {"success": true, "transcript": "..."}
                if not result.get("success", True) is False:
                    transcript = result.get("transcript", "") or result.get("text", "")
                    return transcript
                print(f"Gnani STT error response: {result}")
                return None
            if isinstance(result, str):
                return result
            return None

        except Exception as e:
            print(f"Gnani STT Exception: {e}")
            return None
        finally:
            if cleanup_converted and os.path.exists(converted_path):
                try:
                    os.remove(converted_path)
                except OSError:
                    pass
