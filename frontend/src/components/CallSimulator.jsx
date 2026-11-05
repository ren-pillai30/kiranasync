import { useEffect, useRef, useState } from 'react';
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

export default function CallSimulator(props) {
  const { isOpen } = props;
  const [tabs, setTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const wasOpenRef = useRef(false);
  const nextTabIdRef = useRef(1);

  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      const id = nextTabIdRef.current;
      nextTabIdRef.current += 1;
      setTabs((currentTabs) => [...currentTabs, { id, label: `Call ${id}` }]);
      setActiveTabId(id);
    }
    wasOpenRef.current = isOpen;
  }, [isOpen]);

  return tabs.map((tab) => (
    <CallSimulatorTab
      key={tab.id}
      {...props}
      isOpen={isOpen && tab.id === activeTabId}
      tabs={tabs}
      activeTabId={activeTabId}
      onSelectTab={setActiveTabId}
    />
  ));
}

function CallSimulatorTab({
  isOpen,
  onClose,
  onRefreshStore,
  onOpenBill,
  existingCustomers = [],
  nameDisplayMode = 'en',
  tabs,
  activeTabId,
  onSelectTab,
}) {
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

  useEffect(() => {
    if (!isOpen && callActive) {
      hangUpCall();
    }
  }, [isOpen, callActive, hangUpCall]);

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
          <div className="flex items-center gap-1 overflow-x-auto border-b border-[#D8CEBA] bg-[#F5F0E6] px-4 pt-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => onSelectTab(tab.id)}
                aria-pressed={tab.id === activeTabId}
                className={`shrink-0 rounded-t-lg border border-b-0 px-4 py-1.5 text-xs font-bold transition-colors ${
                  tab.id === activeTabId
                    ? 'border-[#991B1B] bg-[#FAF7F2] text-[#991B1B]'
                    : 'border-[#D8CEBA] bg-[#E9E1D2] text-stone-600 hover:bg-[#FFFDF9]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* HEADER BAR */}
          <div className="flex items-center justify-between px-6 py-3.5 bg-[#991B1B] border-b border-[#7F1D1D]">
            <div className="flex items-center space-x-3">
              <span className="text-2xl p-1 rounded-lg bg-[#FEF3C7]"></span>
              <div>
                <h3 className="text-lg font-black text-[#FFFDF7] flex items-center space-x-2">
                  <span>Virtual Call Simulator</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] font-mono font-bold">
                    Gemini + Gnani AI
                  </span>
                </h3>
                <p className="text-xs text-red-100">
                  Live voice conversation with Gnani speech and Gemini intent parsing. Orders and account changes need your confirmation.
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

                    {item.confirmationRequired && (
                      <div className="mt-3 flex flex-wrap gap-2 border-t border-[#E2D9C8] pt-3">
                        <span className="w-full text-[11px] font-semibold text-[#92400E]">
                          No inventory or account changes will be made until you confirm.
                        </span>
                        <button
                          type="button"
                          onClick={() => sendTextMessage('Yes, I confirm. Please proceed.')}
                          className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-800"
                        >
                          Confirm
                        </button>
                        <button
                          type="button"
                          onClick={() => sendTextMessage('No, cancel that request.')}
                          className="rounded-lg border border-[#D8CEBA] bg-white px-3 py-1.5 text-xs font-bold text-stone-700 hover:bg-stone-100"
                        >
                          Cancel
                        </button>
                      </div>
                    )}

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
          <div className="border-t border-[#E2D9C8] bg-[#F0EDE6] p-3">
            {isMicRecording && (
              <div className="mb-2 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs font-semibold text-red-800">
                <span className="h-2 w-2 animate-pulse rounded-full bg-red-600" />
                <span>Recording voice message… tap the microphone to send</span>
                <div className="ml-auto h-1.5 w-20 overflow-hidden rounded-full bg-red-200">
                  <div
                    className="h-full bg-red-600 transition-all"
                    style={{ width: `${Math.max(10, audioLevel)}%` }}
                  />
                </div>
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendTextMessage();
              }}
              className="flex items-center gap-2"
            >
              <button
                type="button"
                onClick={isMicRecording ? stopMicRecording : startMicRecording}
                disabled={!callActive}
                aria-label={isMicRecording ? 'Stop recording and send voice message' : 'Record voice message'}
                title={isMicRecording ? 'Stop and send voice message' : 'Record voice message'}
                className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-40 ${
                  isMicRecording
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-[#E7E1D6] text-stone-800 hover:bg-[#D8CEBA]'
                }`}
              >
                {isMicRecording ? (
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="9" y="2" width="6" height="12" rx="3" />
                    <path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8" />
                  </svg>
                )}
              </button>

              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={!callActive}
                placeholder={
                  callActive
                    ? 'Type a message'
                    : 'Start a call to send a message'
                }
                className="min-w-0 flex-1 rounded-full border border-[#D8CEBA] bg-white px-4 py-3 text-sm font-medium text-stone-900 placeholder:text-stone-400 focus:border-[#991B1B] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 disabled:opacity-50"
              />

              <button
                type="submit"
                disabled={!callActive || !inputText.trim()}
                aria-label="Send message"
                title="Send message"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#128C7E] text-white transition-colors hover:bg-[#0D776C] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
                  <path d="M3.4 20.4 21 12 3.4 3.6l.1 6.5 12.1 1.9-12.1 1.9-.1 6.5Z" />
                </svg>
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
