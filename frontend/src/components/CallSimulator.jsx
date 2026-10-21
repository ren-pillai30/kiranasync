import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { INDIAN_LANGUAGES } from '../constants/languages';
import { useCallSession } from '../hooks/useCallSession';

const SAMPLE_PROMPTS = [
  { label: 'Check Maggi stock', text: 'Maggi ka kitna stock hai aur price kya hai?' },
  { label: 'Order on cash', text: 'Mujhe 2 packet Tata Salt aur 1 Maggi chahiye.' },
  { label: 'Order on Udhaar', text: '2 Maggi aur 1kg Sugar Ramesh ke udhaar khate mein likh do.' },
  { label: 'Check Ramesh Udhaar', text: 'Ramesh ka kitna udhaar baaki hai?' },
  { label: 'Log ₹200 Udhaar', text: 'Ramesh ke khate mein 200 rupaye udhaar likh do.' },
  { label: 'Customer Repayment', text: 'Ramesh ne 100 rupaye jama kar diye hain.' },
];

export default function CallSimulator({ isOpen, onClose, onRefreshStore, existingCustomers = [] }) {
  const {
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
  } = useCallSession({ onRefreshStore });

  const transcriptEndRef = useRef(null);

  // Auto-scroll transcript log on updates
  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcripts]);

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
                  isMuted
                    ? 'border-red-500/50 text-red-400 bg-red-500/10'
                    : 'border-emerald-500/50 text-emerald-300 bg-emerald-500/10'
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
                  Click <strong className="text-emerald-400">&quot;Simulate Call&quot;</strong> above. Once connected, speak using
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
