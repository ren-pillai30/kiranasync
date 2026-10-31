import { motion, AnimatePresence } from 'framer-motion';

export default function VoiceRecordingHud({
  isActive,
  isRecording,
  lang,
  audioLevel,
  transcript,
  dbAction,
  voiceError,
  t,
  stopAndProcessRecording,
}) {
  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.92 }}
          className="fixed bottom-6 right-6 w-96 bg-[#FFFDF9] border-2 border-[#991B1B] rounded-2xl p-5 shadow-2xl pointer-events-auto z-50 text-stone-900 select-none"
        >
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-[#E2D9C8]">
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isRecording ? 'bg-red-600 animate-ping' : 'bg-[#991B1B]'
                }`}
              />
              <span className="text-xs font-bold uppercase tracking-wider text-[#991B1B]">
                {isRecording
                  ? lang === 'hi'
                    ? 'माइक्रोफ़ोन सुन रहा है...'
                    : 'Microphone Listening...'
                  : t.voiceTitle}
              </span>
            </div>
            {isRecording && (
              <button
                onClick={stopAndProcessRecording}
                className="text-xs px-2.5 py-1 bg-[#991B1B] hover:bg-[#B91C1C] text-white rounded-md font-bold shadow-xs transition-all"
              >
                {lang === 'hi' ? 'भेजें ✓' : 'Send ✓'}
              </button>
            )}
          </div>
          {isRecording && (
            <div className="my-2.5">
              <div className="flex justify-between text-[11px] text-[#78716C] mb-1 font-semibold">
                <span>Input Level</span>
                <span className="text-[#991B1B] font-bold">Auto-sends when you pause</span>
              </div>
              <div className="w-full bg-[#F4EFE6] rounded-full h-2 overflow-hidden border border-[#D8CEBA]">
                <div
                  className="bg-gradient-to-r from-[#FDE68A] via-[#F59E0B] to-[#991B1B] h-full transition-all duration-75"
                  style={{ width: `${Math.max(6, audioLevel)}%` }}
                />
              </div>
            </div>
          )}
          <p className="text-sm font-bold text-stone-900 mb-3 leading-snug">"{transcript}"</p>
          {dbAction && (
            <motion.div
              className={`p-3 rounded-xl flex items-center space-x-2.5 border text-xs font-semibold shadow-2xs ${
                dbAction.status === 'success'
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                  : 'bg-[#FEF3C7] border-[#FDE68A] text-[#92400E]'
              }`}
            >
              <span>{dbAction.status === 'success' ? '✓' : 'ℹ'}</span>
              <span className="leading-snug">{dbAction.message}</span>
            </motion.div>
          )}
          {voiceError && (
            <p role="alert" className="mt-2.5 text-xs text-red-700 bg-red-50 p-2.5 rounded-lg border border-red-200 font-semibold">
              {voiceError}
            </p>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
