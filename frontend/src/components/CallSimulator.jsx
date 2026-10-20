import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import RecordRTC, { StereoAudioRecorder } from 'recordrtc';

const INDIAN_LANGUAGES = [
  { code: 'hi-IN', label: 'Hindi (हिंदी)' },
  { code: 'en-IN', label: 'Indian English' },
  { code: 'ta-IN', label: 'Tamil (தமிழ்)' },
  { code: 'te-IN', label: 'Telugu (తెలుగు)' },
  { code: 'kn-IN', label: 'Kannada (ಕನ್ನಡ)' },
  { code: 'ml-IN', label: 'Malayalam (മലയാളം)' },
  { code: 'mr-IN', label: 'Marathi (मराठी)' },
  { code: 'bn-IN', label: 'Bengali (বাংলা)' },
  { code: 'gu-IN', label: 'Gujarati (ગુજરાતી)' },
  { code: 'pa-IN', label: 'Punjabi (ਪੰਜਾਬੀ)' },
];

const SAMPLE_PROMPTS = [
  { label: 'Check Maggi stock', text: 'Maggi ka kitna stock hai aur price kya hai?' },
  { label: 'Order on cash', text: 'Mujhe 2 packet Tata Salt aur 1 Maggi chahiye.' },
  { label: 'Order on Udhaar', text: '2 Maggi aur 1kg Sugar Ramesh ke udhaar khate mein likh do.' },
  { label: 'Check Ramesh Udhaar', text: 'Ramesh ka kitna udhaar baaki hai?' },
  { label: 'Log ₹200 Udhaar', text: 'Ramesh ke khate mein 200 rupaye udhaar likh do.' },
  { label: 'Customer Repayment', text: 'Ramesh ne 100 rupaye jama kar diye hain.' },
];

export default function CallSimulator({ isOpen, onClose, onRefreshStore, existingCustomers = [] }) {
  const [callActive, setCallActive] = useState(false);
  const [callStatus, setCallStatus] = useState('idle'); // idle | connecting | connected | speaking | listening | ended
  const [callDuration, setCallDuration] = useState(0);
  const [callerName, setCallerName] = useState('Ramesh');
  const [languageCode, setLanguageCode] = useState('hi-IN');
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
  const transcriptEndRef = useRef(null);
  const hangUpRef = useRef(null);

  // Auto-scroll transcript log
  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcripts]);

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

  // Clean up audio & recorder on unmount
  useEffect(() => {
    return () => {
      if (hangUpRef.current) {
        hangUpRef.current();
      }
    };
  }, []);

  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // If running under Vite dev server on port 5173, point WS to backend on 5000
    if (window.location.port === '5173') {
      return `${protocol}//127.0.0.1:5000/ws/call`;
    }
    return `${protocol}//${window.location.host}/ws/call`;
  };

  const playBase64Audio = (audioBase64) => {
    if (isMuted || !audioBase64) return;
    try {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      currentAudioRef.current = audio;
      setCallStatus('speaking');
      audio.onended = () => {
        if (callActive) setCallStatus('connected');
      };
      audio.onerror = () => {
        if (callActive) setCallStatus('connected');
      };
      audio.play().catch((err) => console.warn('Audio auto-play failed:', err));
    } catch (err) {
      console.warn('Playback error:', err);
    }
  };

  const stopMicRecording = () => {
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
      if (callActive) setCallStatus('connected');
    });
  };

  const hangUpCall = () => {
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
  };

  useEffect(() => {
    hangUpRef.current = hangUpCall;
  });

  const handleWebSocketMessage = (data) => {
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

      // If database was modified, trigger store refresh so main UI updates live
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
  };

  const startCall = () => {
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
  };

  const sendTextMessage = (textToSend) => {
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
  };

  // MediaRecorder audio capture
  const startMicRecording = async () => {
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
  };

  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 pointer-events-auto">
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-gray-900 border border-violet-500/40 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden text-gray-200"
        >
          {/* HEADER BAR */}
          <div className="flex items-center justify-between px-6 py-4 bg-gray-800/80 border-b border-gray-700">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">📞</span>
              <div>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <span>Virtual Call Simulator</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/30 font-mono">
                    Gemini 2.5 Flash + Gnani AI
                  </span>
                </h3>
                <p className="text-xs text-gray-400">
                  Simulate incoming customer grocery orders and credit inquiries without a physical phone line
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={`text-xs px-2.5 py-1 rounded-lg border ${
                  isMuted ? 'border-red-500/50 text-red-400 bg-red-500/10' : 'border-emerald-500/50 text-emerald-300 bg-emerald-500/10'
                }`}
                title={isMuted ? 'Voice playback is muted' : 'Voice playback is active'}
              >
                {isMuted ? '🔇 Audio Muted' : '🔊 Voice Output ON'}
              </button>
              <button
                onClick={() => {
                  hangUpCall();
                  onClose();
                }}
                className="text-gray-400 hover:text-white text-xl font-bold px-2 py-1"
                title="Close Call Simulator"
              >
                &times;
              </button>
            </div>
          </div>

          {/* CALL DIALER & STATUS BAR */}
          <div className="px-6 py-3 bg-gray-800/40 border-b border-gray-700/80 flex flex-wrap items-center justify-between gap-4 text-xs">
            {/* CALLER PROFILE */}
            <div className="flex items-center space-x-2">
              <span className="text-gray-400 font-semibold uppercase">Customer:</span>
              <input
                type="text"
                value={callerName}
                onChange={(e) => setCallerName(e.target.value)}
                disabled={callActive}
                className="bg-gray-800 text-white px-2.5 py-1 rounded border border-gray-700 text-xs w-28 focus:outline-none focus:border-violet-500 disabled:opacity-50"
                placeholder="Name"
              />
              {existingCustomers?.length > 0 && !callActive && (
                <select
                  onChange={(e) => setCallerName(e.target.value)}
                  className="bg-gray-800 text-gray-300 px-2 py-1 rounded border border-gray-700 text-xs focus:outline-none"
                  value=""
                >
                  <option value="" disabled>
                    Pick existing customer
                  </option>
                  {existingCustomers.map((c) => (
                    <option key={c.CustomerID} value={c.CustomerName}>
                      {c.CustomerName} (₹{c.OutstandingBalance})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* LANGUAGE SELECTOR */}
            <div className="flex items-center space-x-2">
              <span className="text-gray-400 font-semibold uppercase">Language:</span>
              <select
                value={languageCode}
                onChange={(e) => setLanguageCode(e.target.value)}
                disabled={callActive}
                className="bg-gray-800 text-white px-2.5 py-1 rounded border border-gray-700 text-xs focus:outline-none focus:border-violet-500 disabled:opacity-50"
              >
                {INDIAN_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* CALL DURATION & STATUS INDICATOR */}
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-1.5 font-mono">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    callStatus === 'connected' || callStatus === 'speaking' || callStatus === 'listening'
                      ? 'bg-emerald-400 animate-pulse'
                      : callStatus === 'connecting'
                      ? 'bg-amber-400 animate-ping'
                      : 'bg-gray-500'
                  }`}
                />
                <span className="text-white font-bold">{formatTimer(callDuration)}</span>
                <span className="text-gray-400 text-[11px] capitalize">({callStatus})</span>
              </div>

              {/* ACTION BUTTON */}
              {!callActive ? (
                <button
                  onClick={startCall}
                  className="px-4 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg transition-all"
                >
                  <span>📞</span>
                  <span>Simulate Call</span>
                </button>
              ) : (
                <button
                  onClick={hangUpCall}
                  className="px-4 py-1.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-lg animate-pulse"
                >
                  <span>🔴</span>
                  <span>Hang Up</span>
                </button>
              )}
            </div>
          </div>

          {/* SYSTEM NOTICE BANNER */}
          {systemNotice && (
            <div className="px-6 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-300 text-xs flex justify-between items-center">
              <span>⚠️ {systemNotice}</span>
              <button onClick={() => setSystemNotice(null)} className="text-amber-300 font-bold ml-2">
                &times;
              </button>
            </div>
          )}

          {/* LIVE TRANSCRIPT LOG AREA */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-gray-950/60 min-h-[300px]">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-gray-500 space-y-3">
                <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center text-3xl">
                  🎧
                </div>
                <h4 className="text-base font-semibold text-gray-400">Ready to simulate customer calls</h4>
                <p className="text-xs max-w-md text-gray-500">
                  Click <strong className="text-emerald-400">"Simulate Call"</strong> above. Once connected, speak using
                  your microphone or type below. Try asking for stock, ordering items on udhaar, or checking customer
                  credit.
                </p>
              </div>
            ) : (
              transcripts.map((item) => (
                <div
                  key={item.id}
                  className={`flex flex-col ${
                    item.role === 'customer'
                      ? 'items-end'
                      : item.role === 'assistant'
                      ? 'items-start'
                      : 'items-center'
                  }`}
                >
                  {/* MESSAGE BUBBLE */}
                  <div
                    className={`max-w-[80%] rounded-2xl p-4 shadow-md text-sm ${
                      item.role === 'customer'
                        ? 'bg-blue-600/90 text-white rounded-br-none'
                        : item.role === 'assistant'
                        ? 'bg-gray-800 border border-gray-700 text-gray-100 rounded-bl-none'
                        : 'bg-gray-800/60 text-gray-400 text-xs italic py-2 px-4 rounded-full border border-gray-700/50'
                    }`}
                  >
                    <div className="flex items-center justify-between space-x-2 text-[10px] text-gray-300 mb-1">
                      <span className="font-semibold uppercase tracking-wider">
                        {item.role === 'customer'
                          ? `👤 ${callerName || 'Customer'}`
                          : item.role === 'assistant'
                          ? '🤖 Kirana Voice AI'
                          : 'ℹ️ System'}
                      </span>
                      <span className="opacity-70">{item.timestamp}</span>
                    </div>

                    <p className="leading-relaxed whitespace-pre-wrap">{item.text}</p>

                    {/* REPLAY AUDIO BUTTON */}
                    {item.audioBase64 && (
                      <button
                        onClick={() => playBase64Audio(item.audioBase64)}
                        className="mt-2 text-xs flex items-center space-x-1 text-violet-300 hover:text-white bg-violet-600/20 hover:bg-violet-600/40 px-2 py-0.5 rounded transition-colors"
                      >
                        <span>▶ Replay Voice</span>
                      </button>
                    )}

                    {/* STRUCTURED DATABASE ACTION CARD */}
                    {item.dbResult && item.dbResult.status === 'success' && (
                      <div className="mt-3 p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/40 text-emerald-300 text-xs">
                        <div className="font-semibold flex items-center space-x-1.5 mb-1">
                          <span>📦</span>
                          <span>Database Action Executed:</span>
                        </div>
                        <p>{item.dbResult.message}</p>
                        {item.dbResult.new_balance !== undefined && (
                          <span className="block mt-1 font-mono text-[11px] text-emerald-400">
                            Updated Udhaar Balance: ₹{item.dbResult.new_balance}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>

          {/* QUICK PROMPT CHIPS */}
          <div className="px-6 py-2.5 bg-gray-800/50 border-t border-gray-800 flex items-center space-x-2 overflow-x-auto text-xs">
            <span className="text-gray-400 text-[11px] whitespace-nowrap font-semibold">Try Quick Utterance:</span>
            {SAMPLE_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => {
                  if (!callActive) startCall();
                  setTimeout(() => sendTextMessage(prompt.text), callActive ? 0 : 500);
                }}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-violet-600/30 hover:border-violet-500/40 border border-gray-700 text-gray-300 hover:text-white transition-all text-xs"
              >
                {prompt.label}
              </button>
            ))}
          </div>

          {/* INPUT BAR (SPEECH & TEXT) */}
          <div className="p-4 bg-gray-900 border-t border-gray-800 flex items-center space-x-3">
            {/* MICROPHONE STREAMING BUTTON */}
            <button
              onClick={isMicRecording ? stopMicRecording : startMicRecording}
              disabled={!callActive}
              className={`p-3 rounded-xl border flex items-center justify-center transition-all ${
                isMicRecording
                  ? 'bg-red-600 text-white border-red-400 animate-pulse shadow-lg shadow-red-600/30'
                  : 'bg-gray-800 text-gray-300 hover:text-white border-gray-700 hover:bg-gray-700 disabled:opacity-40'
              }`}
              title={isMicRecording ? 'Click to stop & send audio' : 'Speak into call (Microphone streaming)'}
            >
              <span className="text-lg">🎙️</span>
            </button>

            {/* AUDIO LEVEL BAR IF RECORDING */}
            {isMicRecording ? (
              <div className="flex-1 flex flex-col justify-center px-4 py-2 bg-gray-800/80 rounded-xl border border-red-500/40">
                <div className="flex justify-between text-xs text-red-300 mb-1">
                  <span>Listening to customer voice...</span>
                  <span>Click 🎙️ again to send</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-red-500 h-full transition-all duration-75"
                    style={{ width: `${Math.max(10, audioLevel)}%` }}
                  />
                </div>
              </div>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  sendTextMessage();
                }}
                className="flex-1 flex space-x-2"
              >
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  disabled={!callActive}
                  placeholder={
                    callActive
                      ? 'Type customer query or speak (e.g. "2 packet Maggi becho Ramesh ko")...'
                      : 'Click "Simulate Call" above to begin call simulation'
                  }
                  className="flex-1 bg-gray-800 text-white px-4 py-2.5 rounded-xl border border-gray-700 focus:outline-none focus:border-violet-500 disabled:opacity-50 text-sm"
                />
                <button
                  type="submit"
                  disabled={!callActive || !inputText.trim()}
                  className="px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-semibold text-sm disabled:opacity-40 transition-colors shadow-md"
                >
                  Send
                </button>
              </form>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
