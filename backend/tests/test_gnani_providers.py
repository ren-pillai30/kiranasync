import unittest
from unittest.mock import patch, MagicMock
from backend.app.main import app
from backend.app.providers.gnani_tts import GnaniTTSProvider
from backend.app.providers.gnani_stt import GnaniSTTProvider


class GnaniProviderTests(unittest.TestCase):
    @patch("backend.app.providers.gnani_tts.GnaniTTSProvider.synthesize")
    @patch("backend.app.gemini_understanding.translate_for_speech")
    def test_tts_endpoint_translates_and_synthesizes_selected_language(
        self, translate, synthesize
    ):
        translate.return_value = "चीनी के 5 पैकेट बचे हैं।"
        synthesize.return_value = (b"RIFFaudio", "audio/wav")

        response = app.test_client().post(
            "/api/voice/synthesize",
            json={"text": "Sugar: 5 in stock.", "language_code": "hi-IN"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "audio/wav")
        translate.assert_called_once_with("Sugar: 5 in stock.", "hi-IN")
        synthesize.assert_called_once_with(
            "चीनी के 5 पैकेट बचे हैं।",
            language_code="hi-IN",
        )

    # ---------------------------------------------------------------
    # TTS tests
    # ---------------------------------------------------------------

    @patch.dict("os.environ", {}, clear=True)  # wipe env so fallback also returns ""
    def test_tts_requires_api_key(self):
        """Provider with no key AND no env var must raise 'not configured'."""
        provider = GnaniTTSProvider(api_key="")
        with self.assertRaises(RuntimeError) as ctx:
            provider.synthesize("Namaste")
        self.assertIn("not configured", str(ctx.exception))

    @patch("requests.post")
    def test_tts_successful_synthesis(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"RIFF....WAVEfmt...."
        mock_response.headers = {"Content-Type": "audio/wav"}
        mock_post.return_value = mock_response

        provider = GnaniTTSProvider(api_key="mock-tts-key")
        audio_bytes, content_type = provider.synthesize("Sold 2 Tata Salt", language_code="hi-IN")

        self.assertEqual(content_type, "audio/wav")
        self.assertTrue(audio_bytes.startswith(b"RIFF"))
        mock_post.assert_called_once()

        called_payload = mock_post.call_args[1]["json"]
        # Verify correct Timbre v3.0 payload structure
        self.assertIn(called_payload["model"], ("timbre-v3.0", "timbre-v2.5"))
        self.assertEqual(called_payload["text"], "Sold 2 Tata Salt")
        self.assertIn("voice", called_payload)

    @patch("requests.post")
    def test_tts_reads_env_vars(self, mock_post):
        """synthesize() should use GNANI_TTS_MODEL and GNANI_TTS_VOICE from env."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"audio"
        mock_response.headers = {"Content-Type": "audio/wav"}
        mock_post.return_value = mock_response

        env = {"GNANI_TTS_MODEL": "timbre-v3.0", "GNANI_TTS_VOICE": "Nalini"}
        with patch.dict("os.environ", env):
            provider = GnaniTTSProvider(api_key="test-key")
            provider.synthesize("Test text")

        called_payload = mock_post.call_args[1]["json"]
        self.assertEqual(called_payload["model"], "timbre-v3.0")
        self.assertEqual(called_payload["voice"], "Nalini")

    @patch("requests.post")
    def test_tts_http_error_raises_runtime_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        provider = GnaniTTSProvider(api_key="bad-key")
        with self.assertRaises(RuntimeError) as ctx:
            provider.synthesize("Test")
        self.assertIn("HTTP 401", str(ctx.exception))

    # ---------------------------------------------------------------
    # STT tests
    # ---------------------------------------------------------------

    def test_stt_requires_api_key(self):
        provider = GnaniSTTProvider(api_key="")
        result = provider.transcribe("fake.wav")
        self.assertIsNone(result)

    @patch("builtins.open")
    @patch("requests.post")
    def test_stt_successful_transcription(self, mock_post, mock_open):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"transcript": "do packet maggi"}
        mock_post.return_value = mock_response

        provider = GnaniSTTProvider(api_key="mock-stt-key")
        transcript = provider.transcribe("dummy.wav", language_code="en-IN")
        self.assertEqual(transcript, "do packet maggi")


if __name__ == "__main__":
    unittest.main()
