from __future__ import annotations

import os
import sys


def _env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value or default


def main() -> None:
    """Start Hugging Face speech-to-speech with TALA as its LLM backend."""
    sys.argv = [
        "speech-to-speech",
        "--mode",
        "realtime",
        "--ws_host",
        "0.0.0.0",
        "--ws_port",
        _env("VOICE_PORT", "8765"),
        "--num_pipelines",
        _env("VOICE_NUM_PIPELINES", "1"),
        "--stt",
        "faster-whisper",
        "--faster_whisper_stt_model_name",
        _env("VOICE_STT_MODEL", "small.en"),
        "--faster_whisper_stt_device",
        _env("VOICE_DEVICE", "cpu"),
        "--faster_whisper_stt_compute_type",
        _env("VOICE_STT_COMPUTE_TYPE", "int8"),
        "--llm_backend",
        "chat-completions",
        "--model_name",
        "tala-agent",
        "--responses_api_base_url",
        _env("TALA_AGENT_API_URL", "http://agent-api:8000/v1"),
        "--responses_api_api_key",
        _env("VOICE_INTERNAL_API_KEY", "development-voice-key"),
        "--responses_api_stream",
        "false",
        "--tts",
        "kokoro",
        "--kokoro_device",
        _env("VOICE_DEVICE", "cpu"),
        "--kokoro_voice",
        _env("TALA_VOICE", "af_heart"),
        "--kokoro_lang_code",
        "a",
        "--min_silence_ms",
        _env("VOICE_MIN_SILENCE_MS", "500"),
        "--enable_live_transcription",
        "true",
    ]

    from speech_to_speech.s2s_pipeline import main as run_pipeline

    run_pipeline()


if __name__ == "__main__":
    main()
