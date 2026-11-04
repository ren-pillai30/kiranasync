import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { INDIAN_LANGUAGES } from '../constants/languages';
import { useCallSession } from '../hooks/useCallSession';
import { getEntityName } from '../utils/entityNames';
                <span aria-hidden="true" />
const SAMPLE_PROMPTS = [
  { label: 'Check Maggi stock', text: 'Maggi ka kitna stock hai aur price kya hai?' },
  { label: 'Order on cash', text: 'Mujhe 2 packet Tata Salt aur 1 Maggi chahiye.' },
  { label: 'Check Total Bill', text: 'Mera total bill kitna hua?' },
  { label: 'Order on Udhaar', text: '2 Maggi aur 1kg Sugar Ramesh ke udhaar khate mein likh do.' },
  { label: 'Check Ramesh Udhaar', text: 'Ramesh ka kitna udhaar baaki hai?' },
  { label: 'Log ₹200 Udhaar', text: 'Ramesh ke khate mein 200 rupaye udhaar likh do.' },
  { label: 'Customer Repayment', text: 'Ramesh ne 100 rupaye jama kar diye hain.' },
];

export default function CallSimulator({ isOpen, onClose, onRefreshStore, onOpenBill, existingCustomers = [], nameDisplayMode = 'en' }) {
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
    currentBill,
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
      <div
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 pointer-events-auto cursor-pointer"
        onClick={() => {
          hangUpCall();
          onClose();
        }}
      >
        <motion.div
          initial={{ scale: 0.96, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.96, opacity: 0 }}
          className="bg-[#FAF7F2] border-2 border-[#991B1B] rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden text-stone-900 pointer-events-auto cursor-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* HEADER BAR */}
          <div className="flex items-center justify-between px-6 py-3.5 bg-[#991B1B] border-b border-[#7F1D1D]">
            <div className="flex items-center space-x-3">
              <span className="text-2xl p-1 rounded-lg bg-[#FEF3C7]"></span>
              <div>
                <h3 className="text-lg font-black text-[#FFFDF7] flex items-center space-x-2">
                  <span>Virtual Call Simulator</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] font-mono font-bold">
                    Gemini 2.5 Flash + Gnani AI
                  </span>
                </h3>
                <p className="text-xs text-red-100">
                  Simulate incoming customer grocery orders and credit inquiries without a physical phone line
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={`text-xs px-2.5 py-1 rounded-lg border font-bold transition-all shadow-xs ${
                  isMuted
                    ? 'border-red-300 text-red-950 bg-red-100 hover:bg-red-200'
                    : 'border-[#FDE68A] text-[#78350F] bg-[#FEF3C7] hover:bg-[#FDE68A]'
                }`}
                title={isMuted ? 'Voice playback is muted' : 'Voice playback is active'}
              >
                {isMuted ? ' Audio Muted' : ' Voice Output ON'}
              </button>
              <button
                onClick={() => {
                  hangUpCall();
                  onClose();
                }}
                className="text-white hover:text-red-200 text-2xl font-bold px-2 py-0.5 rounded-lg hover:bg-red-900/40 transition-colors"
                title="Close Call Simulator"
              >
                &times;
              </button>
            </div>
          </div>

          {/* CALL DIALER & STATUS BAR */}
          <div className="px-6 py-3 bg-[#FFFDF9] border-b border-[#E2D9C8] flex flex-wrap items-center justify-between gap-4 text-xs">
            {/* CALLER PROFILE */}
            <div className="flex items-center space-x-2">
              <span className="text-stone-700 font-bold uppercase tracking-wider text-[11px]">Customer:</span>
              <input
                type="text"
                value={callerName}
                onChange={(e) => setCallerName(e.target.value)}
                disabled={callActive}
                className="bg-[#FAF7F2] text-stone-900 px-2.5 py-1.5 rounded-lg border border-[#D8CEBA] text-xs w-32 focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 font-semibold disabled:opacity-50 transition-all"
                placeholder="Name"
              />
              {existingCustomers?.length > 0 && !callActive && (
                <select
                  onChange={(e) => setCallerName(e.target.value)}
                  className="bg-[#FAF7F2] text-stone-800 px-2.5 py-1.5 rounded-lg border border-[#D8CEBA] text-xs font-semibold focus:outline-none transition-all cursor-pointer"
                  value=""
                >
                  <option value="" disabled>
                    Pick existing customer
                  </option>
                  {existingCustomers.map((c) => (
                    <option key={c.CustomerID} value={c.CustomerName}>
                      {getEntityName(c, nameDisplayMode, 'CustomerName', 'CustomerNameHindi')} (₹{c.OutstandingBalance})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* LANGUAGE SELECTOR */}
            <div className="flex items-center space-x-2">
              <span className="text-stone-700 font-bold uppercase tracking-wider text-[11px]">Language:</span>
              <select
                value={languageCode}
                onChange={(e) => setLanguageCode(e.target.value)}
                disabled={callActive}
                className="bg-[#FAF7F2] text-stone-900 px-2.5 py-1.5 rounded-lg border border-[#D8CEBA] text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 disabled:opacity-50 transition-all cursor-pointer"
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
              <div className="flex items-center space-x-1.5 font-mono px-3 py-1 rounded-lg bg-[#FAF7F2] border border-[#D8CEBA]">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    callStatus === 'connected' || callStatus === 'speaking' || callStatus === 'listening'
                      ? 'bg-emerald-500 animate-pulse'
                      : callStatus === 'connecting'
                      ? 'bg-amber-500 animate-ping'
                      : 'bg-stone-400'
                  }`}
                />
                <span className="text-stone-900 font-bold">{formatTimer(callDuration)}</span>
                <span className="text-[#78716C] text-[11px] font-sans font-medium capitalize">({callStatus})</span>
              </div>

              {/* ACTION BUTTON */}
              {!callActive ? (
                <button
                  onClick={startCall}
                  className="px-4 py-1.5 rounded-xl bg-[#991B1B] hover:bg-[#B91C1C] text-white font-bold text-xs flex items-center space-x-1.5 shadow-xs transition-all"
                >
                  <span></span>
                  <span>Simulate Call</span>
                </button>
              ) : (
                <button
                  onClick={hangUpCall}
                  className="px-4 py-1.5 rounded-xl bg-red-700 hover:bg-red-800 text-white font-bold text-xs flex items-center space-x-1.5 shadow-md animate-pulse transition-all"
                >
                  <span></span>
                  <span>Hang Up</span>
                </button>
              )}
            </div>
          </div>

          {/* SYSTEM NOTICE BANNER */}
          {systemNotice && (
            <div className="px-6 py-2 bg-[#FEF3C7] border-b border-[#FDE68A] text-[#92400E] text-xs flex justify-between items-center font-semibold">
              <span> {systemNotice}</span>
              <button onClick={() => setSystemNotice(null)} className="text-[#92400E] font-bold ml-2 hover:opacity-80">
                &times;
              </button>
            </div>
          )}

          {/* LIVE BILL / ORDER SUMMARY BANNER */}
          {currentBill?.items?.length > 0 && (
            <div className="px-6 py-2.5 bg-[#FFFDF9] border-b border-[#E2D9C8] flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-base p-1 rounded bg-[#FEF3C7]"></span>
                <span className="font-bold text-stone-900">
                  Call Order Running Total:
                </span>
                <span className="font-mono font-black text-[#991B1B] text-sm">
                  ₹{Number(currentBill.total || 0).toLocaleString('en-IN')}
                </span>
                <span className="text-[#78716C] font-semibold">
                  ({currentBill.items.length} item{currentBill.items.length > 1 ? 's' : ''})
                </span>
              </div>
              <button
                onClick={() => {
                  if (onOpenBill) {
                    onOpenBill({
                      billItems: currentBill.items,
                      customerName: callerName || 'Customer',
                      paymentMode: 'cash',
                    });
                  }
                }}
                className="px-3 py-1 bg-[#991B1B] hover:bg-[#B91C1C] text-white rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-xs transition-all"
              >
                <span></span>
                <span>View / Print Kirana Bill</span>
              </button>
            </div>
          )}

          {/* LIVE TRANSCRIPT LOG AREA */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-[#F5F0E6] min-h-[300px]">
            {transcripts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-[#78716C] space-y-3">
                <div className="w-16 h-16 rounded-2xl bg-[#FFFDF9] border border-[#D8CEBA] flex items-center justify-center text-3xl shadow-xs" />
                <h4 className="text-base font-bold text-stone-800">Ready to simulate customer calls</h4>
                <p className="text-xs max-w-md text-[#78716C]">
                  Click <strong className="text-[#991B1B]">&quot;Simulate Call&quot;</strong> above. Once connected, speak using
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
                    className={`max-w-[80%] rounded-2xl p-4 shadow-xs text-sm ${
                      item.role === 'customer'
                        ? 'bg-[#FEF3C7] text-[#78350F] border border-[#FDE68A] rounded-br-none'
                        : item.role === 'assistant'
                        ? 'bg-[#FFFDF9] text-stone-900 border border-[#DFD5C3] rounded-bl-none'
                        : 'bg-[#FFFDF9]/80 text-[#78716C] text-xs italic py-2 px-4 rounded-full border border-[#D8CEBA]'
                    }`}
                  >
                    <div className="flex items-center justify-between space-x-2 text-[10px] text-[#78716C] mb-1">
                      <span className="font-bold uppercase tracking-wider">
                        {item.role === 'customer'
                          ? ` ${callerName || 'Customer'}`
                          : item.role === 'assistant'
                          ? ' Kirana Voice AI'
                          : 'System'}
                      </span>
                      <span className="opacity-70 font-mono">{item.timestamp}</span>
                    </div>

                    <p className="leading-relaxed whitespace-pre-wrap font-medium">{item.text}</p>

                    {/* STRUCTURED DATABASE ACTION CARD */}
                    {item.dbResult && item.dbResult.status === 'success' && (
                      <div className="mt-3 p-2.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs">
                        <div className="font-bold flex items-center space-x-1.5 mb-1">
                          <span></span>
                          <span>Database Action Executed:</span>
                        </div>
                        <p>{item.dbResult.message}</p>
                        {item.dbResult.new_balance !== undefined && (
                          <span className="block mt-1 font-mono text-[11px] font-bold text-emerald-800">
                            Updated Udhaar Balance: ₹{item.dbResult.new_balance}
                          </span>
                        )}
                      </div>
                    )}

                    {/* MEASUREMENT MISMATCH CALLOUT */}
                    {(item.dbResult?.status === 'measurement_mismatch' ||
                      (item.actionData?.available_measurements?.length > 0 &&
                        item.actionData?.exact_measurement_available === false)) && (
                      <div className="mt-3 p-2.5 rounded-xl bg-red-50 border border-red-300 text-red-900 text-xs">
                        <div className="font-bold flex items-center space-x-1.5 mb-1 text-red-800">
                          <span></span>
                          <span>Measurement Unavailable in Stock:</span>
                        </div>
                        <p>
                          Exact measurement{' '}
                          <strong>
                            {item.dbResult?.requested_measurement ||
                              item.actionData?.requested_measurement}
                          </strong>{' '}
                          is not available.
                        </p>
                        <p className="mt-1 font-mono text-[11px] text-red-700 font-bold">
                          Available sizes:{' '}
                          {(
                            item.dbResult?.other_measurements ||
                            item.actionData?.available_measurements ||
                            []
                          ).join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>

          {/* QUICK PROMPT CHIPS */}
          <div className="px-6 py-2.5 bg-[#FAF7F2] border-t border-[#E2D9C8] flex items-center space-x-2 overflow-x-auto text-xs">
            <span className="text-stone-700 text-[11px] whitespace-nowrap font-bold">Try Quick Utterance:</span>
            {SAMPLE_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => {
                  if (!callActive) startCall();
                  setTimeout(() => sendTextMessage(prompt.text), callActive ? 0 : 500);
                }}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-[#FFFDF9] hover:bg-[#FEF3C7] hover:border-[#FDE68A] border border-[#D8CEBA] text-stone-800 font-semibold transition-all text-xs shadow-2xs"
              >
                {prompt.label}
              </button>
            ))}
          </div>

          {/* INPUT BAR (SPEECH & TEXT) */}
          <div className="p-4 bg-[#FFFDF9] border-t border-[#E2D9C8] flex items-center space-x-3">
            {/* MICROPHONE STREAMING BUTTON */}
            <button
              onClick={isMicRecording ? stopMicRecording : startMicRecording}
              disabled={!callActive}
              className={`p-3 rounded-xl border flex items-center justify-center transition-all shadow-xs ${
                isMicRecording
                  ? 'bg-red-600 text-white border-red-500 animate-pulse shadow-md shadow-red-900/30'
                  : 'bg-[#FAF7F2] text-stone-800 hover:text-stone-900 border-[#D8CEBA] hover:bg-[#FEF3C7] disabled:opacity-40'
              }`}
              title={isMicRecording ? 'Click to stop & send audio' : 'Speak into call (Microphone streaming)'}
            >
              <span className="text-lg"></span>
            </button>

            {/* AUDIO LEVEL BAR IF RECORDING */}
            {isMicRecording ? (
              <div className="flex-1 flex flex-col justify-center px-4 py-2 bg-red-50 rounded-xl border border-red-300">
                <div className="flex justify-between text-xs text-red-800 mb-1 font-semibold">
                  <span>Listening to customer voice...</span>
                  <span className="font-bold">Click  again to send</span>
                </div>
                <div className="w-full bg-red-200 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-[#991B1B] h-full transition-all duration-75"
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
                  className="flex-1 bg-[#FAF7F2] text-stone-900 placeholder:text-stone-400 px-4 py-2.5 rounded-xl border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] disabled:opacity-50 text-sm font-medium transition-all"
                />
                <button
                  type="submit"
                  disabled={!callActive || !inputText.trim()}
                  className="px-5 py-2.5 bg-[#991B1B] hover:bg-[#B91C1C] text-white rounded-xl font-bold text-sm disabled:opacity-40 transition-all shadow-xs"
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
