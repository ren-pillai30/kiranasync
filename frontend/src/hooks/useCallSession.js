import { useState, useEffect, useRef, useCallback } from 'react';
import RecordRTC, { StereoAudioRecorder } from 'recordrtc';

export function useCallSession({ onRefreshStore, initialCallerName = 'Ramesh', initialLangCode = 'hi-IN' } = {}) {
  const [callActive, setCallActive] = useState(false);
  const [callStatus, setCallStatus] = useState('idle'); // idle | connecting | connected | speaking | listening | ended
  const [callDuration, setCallDuration] = useState(0);
  const [callerName, setCallerName] = useState(initialCallerName);
  const [languageCode, setLanguageCode] = useState(initialLangCode);
  const [transcripts, setTranscripts] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isMicRecording, setIsMicRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [systemNotice, setSystemNotice] = useState(null);

  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const recorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const currentAudioRef = useRef(null);
  const hangUpRef = useRef(null);

  // Call duration timer
  useEffect(() => {
    if (callActive) {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [callActive]);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (window.location.port === '5173') {
      return `${protocol}//127.0.0.1:5000/ws/call`;
    }
    return `${protocol}//${window.location.host}/ws/call`;
  }, []);

  const playBase64Audio = useCallback((audioBase64) => {
    if (isMuted || !audioBase64) return;
    try {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      currentAudioRef.current = audio;
      setCallStatus('speaking');
      audio.onended = () => {
        setCallStatus((prev) => (prev === 'speaking' ? 'connected' : prev));
      };
      audio.onerror = () => {
        setCallStatus((prev) => (prev === 'speaking' ? 'connected' : prev));
      };
      audio.play().catch((err) => console.warn('Audio auto-play failed:', err));
    } catch (err) {
      console.warn('Playback error:', err);
    }
  }, [isMuted]);

  const stopMicRecording = useCallback(() => {
    if (!recorderRef.current) return;

    recorderRef.current.stopRecording(() => {
      const blob = recorderRef.current.getBlob();
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = reader.result.split(',')[1];
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && base64data) {
          wsRef.current.send(
            JSON.stringify({
              type: 'audio_input',
              audio_base64: base64data,
              language_code: languageCode,
            })
          );
        }
      };
      reader.readAsDataURL(blob);

      if (recorderRef.current.camera) {
        recorderRef.current.camera.getTracks().forEach((track) => track.stop());
      }
      recorderRef.current = null;
      setIsMicRecording(false);
      setAudioLevel(0);
      setCallStatus((prev) => (prev === 'listening' ? 'connected' : prev));
    });
  }, [languageCode]);

  const hangUpCall = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
    }
    stopMicRecording();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'end_call' }));
        wsRef.current.close();
      } catch (err) {
        console.warn('Error closing websocket:', err);
      }
    }
    setCallActive(false);
    setCallStatus('idle');
    setCallDuration(0);
  }, [stopMicRecording]);

  useEffect(() => {
    hangUpRef.current = hangUpCall;
  }, [hangUpCall]);

  useEffect(() => {
    return () => {
      if (hangUpRef.current) {
        hangUpRef.current();
      }
    };
  }, []);

  const handleWebSocketMessage = useCallback((data) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    if (data.type === 'call_connected') {
      setTranscripts((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          text: data.reply_text,
          audioBase64: data.audio_base64,
          timestamp,
        },
      ]);
      if (data.audio_base64) {
        playBase64Audio(data.audio_base64);
      }
    } else if (data.type === 'transcript') {
      setTranscripts((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: data.role || 'customer',
          text: data.text,
          timestamp,
        },
      ]);
    } else if (data.type === 'call_response') {
      setTranscripts((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          text: data.reply_text,
          audioBase64: data.audio_base64,
          actionType: data.action_type,
          actionData: data.action_data,
          dbResult: data.db_result,
          timestamp,
        },
      ]);

      if (data.audio_base64) {
        playBase64Audio(data.audio_base64);
      }

      if (data.db_result && data.db_result.status === 'success') {
        if (onRefreshStore) onRefreshStore();
      }
    } else if (data.type === 'call_ended') {
      setTranscripts((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'system',
          text: data.reply_text || 'Call completed.',
          timestamp,
        },
      ]);
      if (data.audio_base64) {
        playBase64Audio(data.audio_base64);
      }
      setCallActive(false);
      setCallStatus('ended');
    } else if (data.type === 'error') {
      setSystemNotice(data.error);
    }
  }, [onRefreshStore, playBase64Audio]);

  const startCall = useCallback(() => {
    setCallDuration(0);
    setCallStatus('connecting');
    setSystemNotice(null);
    const wsUrl = getWebSocketUrl();

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setCallActive(true);
        setCallStatus('connected');
        ws.send(
          JSON.stringify({
            type: 'start_call',
            customer_name: callerName || 'Customer',
            language_code: languageCode,
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (err) => {
        console.error('Call WebSocket error:', err);
        setSystemNotice('WebSocket connection failed. Ensure KiranaSync backend is running on port 5000.');
        setCallStatus('idle');
        setCallActive(false);
      };

      ws.onclose = () => {
        setCallActive(false);
        setCallStatus('ended');
      };
    } catch (err) {
      console.error('Connection failed:', err);
      setSystemNotice('Could not initiate call session.');
      setCallStatus('idle');
    }
  }, [callerName, getWebSocketUrl, handleWebSocketMessage, languageCode]);

  const sendTextMessage = useCallback((textToSend) => {
    const text = (textToSend || inputText).trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setTranscripts((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'customer',
        text,
        timestamp,
      },
    ]);

    wsRef.current.send(
      JSON.stringify({
        type: 'text_input',
        text,
        language_code: languageCode,
      })
    );

    setInputText('');
  }, [inputText, languageCode]);

  const startMicRecording = useCallback(async () => {
    if (!callActive || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      alert('Please start the call first before speaking.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const levelInterval = setInterval(() => {
        if (!recorderRef.current) {
          clearInterval(levelInterval);
          return;
        }
        analyser.getByteFrequencyData(dataArray);
        const sum = dataArray.reduce((acc, val) => acc + val, 0);
        const avg = sum / dataArray.length;
        setAudioLevel(Math.min(100, Math.round((avg / 60) * 100)));
      }, 100);

      const recorder = new RecordRTC(stream, {
        type: 'audio',
        mimeType: 'audio/wav',
        recorderType: StereoAudioRecorder,
        numberOfAudioChannels: 1,
        desiredSampRate: 16000,
      });

      recorder.startRecording();
      recorderRef.current = recorder;
      setIsMicRecording(true);
      setCallStatus('listening');
    } catch (err) {
      console.error('Microphone error:', err);
      setSystemNotice('Microphone access denied. You can still test via the text box below.');
    }
  }, [callActive]);

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  return {
    callActive,
    callStatus,
    callDuration,
    callerName,
    setCallerName,
    languageCode,
    setLanguageCode,
    transcripts,
    inputText,
    setInputText,
    isMuted,
    setIsMuted,
    isMicRecording,
    audioLevel,
    systemNotice,
    setSystemNotice,
    startCall,
    hangUpCall,
    sendTextMessage,
    startMicRecording,
    stopMicRecording,
    formatTimer,
  };
}

