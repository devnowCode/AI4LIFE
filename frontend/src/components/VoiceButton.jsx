import { useState, useRef } from "react";
import { Mic, Square } from "lucide-react";
import { transcribe } from "@/lib/api";
import { toast } from "sonner";

/**
 * Voice input button. Records with MediaRecorder API and pipes to /api/transcribe.
 */
export const VoiceButton = ({ onTranscribed, disabled }) => {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  const start = async () => {
    if (disabled || busy) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      rec.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setBusy(true);
        try {
          const { text } = await transcribe(blob, "it");
          if (text?.trim()) {
            onTranscribed(text.trim());
            toast.success("Trascritto");
          } else {
            toast.error("Trascrizione vuota");
          }
        } catch (e) {
          toast.error("Errore Whisper: " + (e?.response?.data?.detail || e.message));
        } finally {
          setBusy(false);
        }
      };
      recorderRef.current = rec;
      rec.start();
      setRecording(true);
    } catch (e) {
      toast.error("Microfono non disponibile: " + e.message);
    }
  };

  const stop = () => {
    if (recorderRef.current && recording) {
      recorderRef.current.stop();
      setRecording(false);
    }
  };

  return (
    <button
      data-testid="voice-btn"
      onClick={recording ? stop : start}
      disabled={disabled || busy}
      className={`p-2 rounded-lg transition-colors ${
        recording
          ? "text-rose-300 bg-rose-500/15 border border-rose-500/30 beam"
          : busy
            ? "text-slate-500 bg-slate-800/50"
            : "text-slate-400 hover:text-sky-300 hover:bg-slate-800/50"
      } disabled:opacity-40 disabled:cursor-not-allowed`}
      title={recording ? "Ferma registrazione" : "Dettatura vocale"}
    >
      {recording
        ? <Square strokeWidth={2} className="w-4 h-4" />
        : <Mic strokeWidth={1.5} className="w-4 h-4" />}
    </button>
  );
};
