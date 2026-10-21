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
          initial={{ opacity: 0, y: 50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.9 }}
          className="fixed bottom-6 right-6 w-96 bg-gray-900/95 backdrop-blur-md border border-gray-700/80 rounded-2xl p-5 shadow-2xl pointer-events-auto z-50"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isRecording ? 'bg-red-500 animate-ping' : 'bg-emerald-500'
                }`}
              />
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
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
                className="text-xs px-2.5 py-1 bg-red-600 hover:bg-red-500 text-white rounded-md font-semibold shadow transition-colors"
              >
                {lang === 'hi' ? 'भेजें ✓' : 'Send ✓'}
              </button>
            )}
          </div>
          {isRecording && (
            <div className="my-2">
              <div className="flex justify-between text-[11px] text-gray-400 mb-1">
                <span>Voice Input Level</span>
                <span className="text-emerald-400 font-medium">Auto-sends when you pause</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden border border-gray-700">
                <div
                  className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full transition-all duration-75"
                  style={{ width: `${Math.max(6, audioLevel)}%` }}
                />
              </div>
            </div>
          )}
          <p className="text-base font-semibold text-white mb-4 leading-snug">"{transcript}"</p>
          {dbAction && (
            <motion.div
              className={`p-3 rounded-xl flex items-center space-x-3 border ${
                dbAction.status === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                  : 'bg-blue-500/10 border-blue-500/40 text-blue-300'
              }`}
            >
              <span className="text-sm font-medium">{dbAction.message}</span>
            </motion.div>
          )}
          {voiceError && (
            <p role="alert" className="mt-3 text-sm text-red-300">
              {voiceError}
            </p>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
