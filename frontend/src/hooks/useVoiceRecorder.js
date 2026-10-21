import { useState, useRef } from 'react';
import RecordRTC, { StereoAudioRecorder } from 'recordrtc';
import { api } from '../services/api';

export function useVoiceRecorder({
  selectedLangCode,
  onSpeechDetected,
  onProcessing,
  onSuccess,
  onError,
  onMicError,
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const recordRTC = useRef(null);
  const mediaStreamRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioContextRef = useRef(null);
  const vadIntervalRef = useRef(null);
  const playbackAudioContextRef = useRef(null);

  const cleanupAudioNodes = () => {
    if (recordingTimerRef.current) {
      clearTimeout(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {
        /* ignore */
      }
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  };

  const stopAndProcessRecording = () => {
    cleanupAudioNodes();

    if (recordRTC.current) {
      setIsRecording(false);
      if (onProcessing) onProcessing();

      try {
        recordRTC.current.stopRecording(async () => {
          const audioBlob = recordRTC.current.getBlob();
          if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach((track) => track.stop());
            mediaStreamRef.current = null;
          }

          const formData = new FormData();
          formData.append('audio', audioBlob, 'command.wav');
          formData.append('lang', selectedLangCode);

          try {
            const data = await api.processAudio(formData);
            if (data.status === 'success') {
              if (onSuccess) onSuccess(data);
            } else {
              if (onError) onError(data.error || 'Failed to process audio');
            }
          } catch (err) {
            console.error('Audio processing failed:', err);
            if (onError) onError(err.message || 'Network connection failed');
          }
        });
      } catch (err) {
        console.error('Stop recording error:', err);
        setIsRecording(false);
      }
    }
  };

  const startRecording = async () => {
    if (isRecording) {
      stopAndProcessRecording();
      return;
    }

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) {
      try {
        if (!playbackAudioContextRef.current) {
          playbackAudioContextRef.current = new AudioCtx();
        }
        if (playbackAudioContextRef.current.state === 'suspended') {
          playbackAudioContextRef.current.resume().catch((err) => {
            console.warn('Audio playback unlock failed:', err);
          });
        }
      } catch (err) {
        console.warn('Audio playback initialization failed:', err);
      }
    }

    try {
      if (onSpeechDetected) onSpeechDetected();
      setIsRecording(true);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      recordRTC.current = new RecordRTC(stream, {
        type: 'audio',
        mimeType: 'audio/wav',
        recorderType: StereoAudioRecorder,
        desiredSampRate: 16000,
        numberOfAudioChannels: 1,
      });

      recordRTC.current.startRecording();

      // Voice Activity Detection (VAD) via Web Audio API Analyser
      try {
        if (AudioCtx) {
          const audioCtx = new AudioCtx();
          audioContextRef.current = audioCtx;
          const source = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 256;
          source.connect(analyser);

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          let speechDetected = false;
          let silenceMs = 0;
          const CHECK_INTERVAL_MS = 100;
          const SPEECH_THRESHOLD = 14;
          const SILENCE_TIMEOUT_MS = 1800; // Auto-stop 1.8s after speech ends

          vadIntervalRef.current = setInterval(() => {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            setAudioLevel(Math.min(100, Math.round((avg / 64) * 100)));

            if (avg > SPEECH_THRESHOLD) {
              speechDetected = true;
              silenceMs = 0;
            } else if (speechDetected) {
              silenceMs += CHECK_INTERVAL_MS;
              if (silenceMs >= SILENCE_TIMEOUT_MS) {
                stopAndProcessRecording();
              }
            }
          }, CHECK_INTERVAL_MS);
        }
      } catch (vadErr) {
        console.warn('VAD init warning:', vadErr);
      }

      // Max safety timeout (16 seconds)
      recordingTimerRef.current = setTimeout(() => {
        stopAndProcessRecording();
      }, 16000);
    } catch (err) {
      console.warn('Microphone access error:', err);
      setIsRecording(false);
      if (onMicError) onMicError();
    }
  };

  return {
    isRecording,
    audioLevel,
    startRecording,
    stopAndProcessRecording,
    playbackAudioContextRef,
  };
}

