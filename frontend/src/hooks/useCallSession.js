import { useState, useEffect, useRef, useCallback } from 'react';
import RecordRTC, { StereoAudioRecorder } from 'recordrtc';

async function readCallResponse(response, fallbackMessage) {
  const contentType = response.headers.get('content-type') || '';
  const responseText = await response.text();
  let data;

  try {
    data = JSON.parse(responseText);
  } catch {
    const isHtml = contentType.includes('text/html') || /^\s*<!doctype html|^\s*<html/i.test(responseText);
    if (isHtml) {
      throw new Error(
        `Call API returned an HTML page (HTTP ${response.status}). Check the Vercel function logs and API route configuration.`
      );
    }
    throw new Error(
      responseText.slice(0, 200) || `Call API returned an invalid response (HTTP ${response.status}).`
    );
  }

  if (!response.ok) {
    throw new Error(data.error || data.detail || fallbackMessage);
  }
  return data;
}

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
  const [currentBill, setCurrentBill] = useState({ items: [], total: 0 });

  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const recorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const currentAudioRef = useRef(null);
  const hangUpRef = useRef(null);
  const sendAudioBlobRef = useRef(null);

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

  const isWebSocketAvailable = useCallback(
    () => window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
    []
  );

  const playBase64Audio = useCallback((audioBase64, contentType = 'audio/wav') => {
    if (isMuted || !audioBase64) {
      setCallStatus('connected');
      return;
    }
    try {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
      const audio = new Audio(`data:${contentType};base64,${audioBase64}`);
      currentAudioRef.current = audio;
      setCallStatus('speaking');
      audio.onended = () => {
        setCallStatus((prev) => (prev === 'speaking' ? 'connected' : prev));
      };
      audio.onerror = () => {
        setCallStatus((prev) => (prev === 'speaking' ? 'connected' : prev));
        setSystemNotice('The reply audio could not be played. Check your audio output and try again.');
      };
      audio.play().catch((err) => {
        console.warn('Audio auto-play failed:', err);
        setCallStatus('connected');
        setSystemNotice('The reply audio could not start. Tap the page and try again.');
      });
    } catch (err) {
      console.warn('Playback error:', err);
      setSystemNotice('The reply audio could not be played.');
    }
  }, [isMuted]);

  const stopMicRecording = useCallback(() => {
    if (!recorderRef.current) return;

    const recorder = recorderRef.current;
    recorder.stopRecording(() => {
      const blob = recorder.getBlob();
      if (recorder.camera) {
        recorder.camera.getTracks().forEach((track) => track.stop());
      }
      recorderRef.current = null;
      setIsMicRecording(false);
      setAudioLevel(0);
      setCallStatus((prev) => (prev === 'listening' ? 'connected' : prev));
      if (blob && sendAudioBlobRef.current) sendAudioBlobRef.current(blob);
    });
  }, []);

  const hangUpCall = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
    }
    if (recorderRef.current) {
      const recorder = recorderRef.current;
      recorder.stopRecording(() => {
        if (recorder.camera) {
          recorder.camera.getTracks().forEach((track) => track.stop());
        }
      });
      recorderRef.current = null;
      setIsMicRecording(false);
      setAudioLevel(0);
    }

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
  }, []);

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
          audioContentType: data.audio_content_type || 'audio/wav',
          timestamp,
        },
      ]);
      if (data.audio_base64) {
        playBase64Audio(data.audio_base64, data.audio_content_type || 'audio/wav');
      } else {
        setCallStatus('connected');
        if (data.audio_error) setSystemNotice(data.audio_error);
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
      if (data.customer_text) {
        setTranscripts((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'customer' && last.text === data.customer_text) return prev;
          return [
            ...prev,
            {
              id: `${Date.now()}-customer`,
              role: 'customer',
              text: data.customer_text,
              timestamp,
            },
          ];
        });
      }
      setTranscripts((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          text: data.reply_text,
          audioBase64: data.audio_base64,
          audioContentType: data.audio_content_type || 'audio/wav',
          actionType: data.action_type,
          actionData: data.action_data,
          dbResult: data.db_result,
          confirmationRequired: data.confirmation_required,
          timestamp,
        },
      ]);

      if (data.audio_base64) {
        playBase64Audio(data.audio_base64, data.audio_content_type || 'audio/wav');
      } else {
        setCallStatus('connected');
        if (data.audio_error) setSystemNotice(data.audio_error);
      }
      if (data.error) setSystemNotice(data.error);

      if (data.db_result && data.db_result.status === 'success') {
        if (onRefreshStore) onRefreshStore();
      }

      // Track running bill from session
      if (data.current_bill) {
        setCurrentBill({
          items: data.current_bill.items || [],
          total: data.current_bill.total || 0,
        });
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

  const startRestCall = useCallback(async () => {
    try {
      const response = await fetch('/api/call/http/start', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caller_name: callerName, language_code: languageCode }),
      });
      const data = await readCallResponse(response, 'Could not start the call.');
      setSystemNotice(null);
      setCallActive(true);
      setCallStatus('connected');
      handleWebSocketMessage({
        type: 'call_connected',
        reply_text: data.reply_text,
        audio_base64: data.audio_base64,
        audio_content_type: data.audio_content_type,
        audio_error: data.audio_error,
      });
    } catch (error) {
      console.error('Call start failed:', error);
      setSystemNotice(error.message || 'Could not start call session.');
      setCallStatus('idle');
      setCallActive(false);
    }
  }, [callerName, handleWebSocketMessage, languageCode]);

  const startCall = useCallback(() => {
    setCallDuration(0);
    setCallStatus('connecting');
    setSystemNotice(null);
    setCurrentBill({ items: [], total: 0 });
    setTranscripts([]);
    if (!isWebSocketAvailable()) {
      startRestCall();
      return;
    }

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
        setSystemNotice('WebSocket unavailable. Switching to the voice call connection.');
        wsRef.current = null;
        startRestCall();
      };

      ws.onclose = () => {
        if (wsRef.current === ws) {
          setCallActive(false);
          setCallStatus('ended');
          wsRef.current = null;
        }
      };
    } catch (err) {
      console.error('Connection failed:', err);
      setSystemNotice('Could not initiate call session.');
      setCallStatus('idle');
    }
  }, [
    callerName,
    getWebSocketUrl,
    handleWebSocketMessage,
    isWebSocketAvailable,
    languageCode,
    startRestCall,
  ]);

  const sendTextMessage = useCallback((textToSend) => {
    const text = (textToSend || inputText).trim();
    if (!text) return;

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

    if (!isWebSocketAvailable()) {
      fetch('/api/call/http/turn', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: text,
          caller_name: callerName,
          language_code: languageCode,
          conversation_history: transcripts,
        }),
      })
        .then(async (response) => {
          const data = await readCallResponse(response, 'Call request failed.');
          handleWebSocketMessage({
            type: 'call_response',
            reply_text: data.reply_text,
            audio_base64: data.audio_base64,
            audio_content_type: data.audio_content_type,
            audio_error: data.audio_error,
            action_type: data.action_type,
            action_data: data.action_data,
            db_result: data.db_result,
            current_bill: data.current_bill,
            confirmation_required: data.confirmation_required,
          });
        })
        .catch((error) => {
          console.error('Call REST request failed:', error);
          setSystemNotice(error.message || 'Could not process call message.');
        });
    } else if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'text_input',
          text,
          language_code: languageCode,
        })
      );
    }

    setInputText('');
  }, [callerName, handleWebSocketMessage, inputText, isWebSocketAvailable, languageCode, transcripts]);

  const sendAudioBlob = useCallback(async (blob) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = reader.result.split(',')[1];
        if (base64data) {
          wsRef.current.send(JSON.stringify({
            type: 'audio_input',
            audio_base64: base64data,
            language_code: languageCode,
          }));
        }
      };
      reader.readAsDataURL(blob);
      return;
    }

    const formData = new FormData();
    formData.append('audio', blob, 'call-audio.wav');
    formData.append('caller_name', callerName);
    formData.append('language_code', languageCode);
    formData.append('conversation_history', JSON.stringify(transcripts));
    try {
      setCallStatus('connecting');
      const response = await fetch('/api/call/http/turn', {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      const data = await readCallResponse(response, 'Could not process call audio.');
      handleWebSocketMessage({
        type: 'call_response',
        customer_text: data.transcript_text,
        reply_text: data.reply_text,
        audio_base64: data.audio_base64,
        audio_content_type: data.audio_content_type,
        audio_error: data.audio_error,
        action_type: data.action_type,
        action_data: data.action_data,
        db_result: data.db_result,
        current_bill: data.current_bill,
        confirmation_required: data.confirmation_required,
      });
    } catch (error) {
      console.error('Call audio request failed:', error);
      setSystemNotice(error.message || 'Could not process call audio.');
      setCallStatus('connected');
    }
  }, [callerName, handleWebSocketMessage, languageCode, transcripts]);

  useEffect(() => {
    sendAudioBlobRef.current = sendAudioBlob;
  }, [sendAudioBlob]);

  const startMicRecording = useCallback(async () => {
    if (!callActive) {
      setSystemNotice('Start the call before recording a message.');
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
    currentBill,
  };
}
