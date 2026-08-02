"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type TalaVoiceStatus =
  | "idle"
  | "connecting"
  | "listening"
  | "user-speaking"
  | "thinking"
  | "speaking"
  | "error";

type TalaVoiceOptions = {
  audioRef: React.RefObject<HTMLAudioElement | null>;
  onUserTranscript: (text: string) => void;
  onAssistantTranscript: (text: string) => void;
};

type RealtimeEvent = {
  type?: string;
  transcript?: string;
  response_id?: string;
  response?: { id?: string; status?: string };
  error?: { message?: string };
};

const ICE_WAIT_MS = 3_000;
const DATA_CHANNEL_WAIT_MS = 20_000;

function waitForIce(pc: RTCPeerConnection) {
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise<void>((resolve) => {
    const finish = () => {
      window.clearTimeout(timeout);
      pc.removeEventListener("icegatheringstatechange", check);
      resolve();
    };
    const check = () => {
      if (pc.iceGatheringState === "complete") finish();
    };
    const timeout = window.setTimeout(finish, ICE_WAIT_MS);
    pc.addEventListener("icegatheringstatechange", check);
  });
}

function waitForDataChannel(channel: RTCDataChannel) {
  if (channel.readyState === "open") return Promise.resolve();
  return new Promise<void>((resolve, reject) => {
    const finish = () => {
      window.clearTimeout(timeout);
      channel.removeEventListener("open", opened);
      channel.removeEventListener("close", closed);
      channel.removeEventListener("error", closed);
    };
    const opened = () => {
      finish();
      resolve();
    };
    const closed = () => {
      finish();
      reject(new Error("Voice connection closed before it was ready"));
    };
    const timeout = window.setTimeout(() => {
      finish();
      reject(new Error("Voice connection timed out"));
    }, DATA_CHANNEL_WAIT_MS);
    channel.addEventListener("open", opened);
    channel.addEventListener("close", closed);
    channel.addEventListener("error", closed);
  });
}

export function useTalaVoice({
  audioRef,
  onUserTranscript,
  onAssistantTranscript,
}: TalaVoiceOptions) {
  const [status, setStatus] = useState<TalaVoiceStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const peerRef = useRef<RTCPeerConnection | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);
  const micRef = useRef<MediaStream | null>(null);
  const callLocationRef = useRef<string | null>(null);
  const assistantSegmentsRef = useRef(new Map<string, string>());
  const callbacksRef = useRef({ onUserTranscript, onAssistantTranscript });

  useEffect(() => {
    callbacksRef.current = { onUserTranscript, onAssistantTranscript };
  }, [onAssistantTranscript, onUserTranscript]);

  const supported =
    typeof window !== "undefined" &&
    "RTCPeerConnection" in window &&
    Boolean(navigator.mediaDevices?.getUserMedia);

  const teardown = useCallback(() => {
    const location = callLocationRef.current;
    callLocationRef.current = null;
    if (location) {
      void fetch(location, { method: "DELETE" }).catch(() => undefined);
    }
    channelRef.current?.close();
    channelRef.current = null;
    peerRef.current?.close();
    peerRef.current = null;
    micRef.current?.getTracks().forEach((track) => track.stop());
    micRef.current = null;
    assistantSegmentsRef.current.clear();
    if (audioRef.current) audioRef.current.srcObject = null;
  }, [audioRef]);

  const stop = useCallback(() => {
    teardown();
    setError(null);
    setStatus("idle");
  }, [teardown]);

  const start = useCallback(async () => {
    if (!supported || peerRef.current) return;
    setError(null);
    setStatus("connecting");

    try {
      const mic = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micRef.current = mic;

      const pc = new RTCPeerConnection();
      peerRef.current = pc;
      const micTrack = mic.getAudioTracks()[0];
      if (!micTrack) throw new Error("No microphone was found");
      micTrack.enabled = false;
      pc.addTrack(micTrack, mic);

      pc.addEventListener("track", (event) => {
        const stream = event.streams[0] ?? new MediaStream([event.track]);
        if (!audioRef.current) return;
        audioRef.current.srcObject = stream;
        void audioRef.current.play().catch(() => undefined);
      });
      pc.addEventListener("connectionstatechange", () => {
        if (pc.connectionState === "failed") {
          setError("The voice connection was lost. Please try again.");
          setStatus("error");
          teardown();
        }
      });

      const channel = pc.createDataChannel("oai-events", { ordered: true });
      channelRef.current = channel;
      channel.addEventListener("close", () => {
        if (!peerRef.current) return;
        setError("The voice connection closed. Please try again.");
        setStatus("error");
        teardown();
      });
      channel.addEventListener("message", (message) => {
        let event: RealtimeEvent;
        try {
          event = JSON.parse(String(message.data)) as RealtimeEvent;
        } catch {
          return;
        }

        switch (event.type) {
          case "session.created":
            channel.send(
              JSON.stringify({
                type: "session.update",
                session: {
                  type: "realtime",
                  instructions:
                    "You are TALA, BAIA's warm digital concierge. Speak naturally and keep voice answers concise.",
                  audio: {
                    input: {
                      turn_detection: {
                        type: "server_vad",
                        interrupt_response: true,
                      },
                    },
                    output: { voice: "af_heart" },
                  },
                },
              }),
            );
            micTrack.enabled = true;
            setStatus("listening");
            break;
          case "input_audio_buffer.speech_started":
            setStatus("user-speaking");
            break;
          case "input_audio_buffer.speech_stopped":
          case "response.created":
            setStatus("thinking");
            break;
          case "conversation.item.input_audio_transcription.completed":
            if (event.transcript?.trim()) {
              callbacksRef.current.onUserTranscript(event.transcript.trim());
            }
            break;
          case "response.output_audio_transcript.done": {
            const responseId = event.response_id ?? "current";
            const segment = event.transcript?.trim();
            if (!segment) break;
            const previous = assistantSegmentsRef.current.get(responseId) ?? "";
            const merged = previous
              ? segment.startsWith(previous)
                ? segment
                : `${previous} ${segment}`
              : segment;
            assistantSegmentsRef.current.set(responseId, merged);
            setStatus("speaking");
            break;
          }
          case "response.done": {
            const responseId = event.response?.id ?? "current";
            const transcript = assistantSegmentsRef.current.get(responseId);
            if (transcript) {
              callbacksRef.current.onAssistantTranscript(transcript);
              assistantSegmentsRef.current.delete(responseId);
            }
            setStatus("listening");
            break;
          }
          case "error":
            setError(event.error?.message ?? "TALA voice encountered an error");
            setStatus("error");
            teardown();
            break;
        }
      });

      await pc.setLocalDescription(await pc.createOffer());
      await waitForIce(pc);
      const offer = pc.localDescription?.sdp;
      if (!offer) throw new Error("Could not create a voice connection");

      const response = await fetch("/api/voice/calls", {
        method: "POST",
        headers: { "Content-Type": "application/sdp" },
        body: offer,
      });
      if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(
          response.status === 503
            ? "TALA is helping another guest. Please try again shortly."
            : detail || "TALA voice is unavailable",
        );
      }
      callLocationRef.current = response.headers.get("location");
      await pc.setRemoteDescription({ type: "answer", sdp: await response.text() });
      await waitForDataChannel(channel);
    } catch (cause) {
      teardown();
      setError(
        cause instanceof Error
          ? cause.message
          : "TALA voice could not start. Please try again.",
      );
      setStatus("error");
    }
  }, [audioRef, supported, teardown]);

  useEffect(() => teardown, [teardown]);

  return { status, error, supported, start, stop };
}
