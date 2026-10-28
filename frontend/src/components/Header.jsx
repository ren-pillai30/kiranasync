import { INDIAN_LANGUAGES } from '../constants/languages';

export default function Header({
  selectedLangCode,
  setSelectedLangCode,
  isMuted,
  setIsMuted,
  isRecording,
  startRecording,
  onOpenSimulator,
  onOpenBill,
  onOpenFeedback,
  handleMinimize,
  handleClose,
}) {
  return (
    <header className="overlay-header absolute top-0 left-0 w-full flex justify-between items-center px-4 py-2 bg-gray-950/95 backdrop-blur-md border-b border-gray-800 pointer-events-auto z-50 shadow-md">
      {/* BRAND & POS COUNTER BADGE */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-black text-white tracking-widest uppercase">
            KIRANA<span className="text-emerald-400">SYNC</span>
          </span>
          <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>POS COUNTER #1</span>
          </span>
        </div>

        <div className="h-4 w-px bg-gray-700"></div>

        {/* LANGUAGE SELECT */}
        <select
          value={selectedLangCode}
          onChange={(e) => setSelectedLangCode(e.target.value)}
          className="bg-gray-900 text-gray-200 text-xs px-2 py-1 rounded-lg border border-gray-700 focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
          title="Select Spoken Language"
        >
          {INDIAN_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>

        {/* AUDIO MUTE TOGGLE */}
        <button
          onClick={() => setIsMuted(!isMuted)}
          className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-all ${
            isMuted
              ? 'border-red-500/50 text-red-400 bg-red-500/10 hover:bg-red-500/20'
              : 'border-emerald-500/50 text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20'
          }`}
          title={isMuted ? 'Audio feedback is muted' : 'Audio feedback is active (Gnani Timbre)'}
        >
          {isMuted ? '🔇 Audio Muted' : '🔊 Voice Output ON'}
        </button>

        {/* VOICE COMMAND BUTTON */}
        <button
          onClick={startRecording}
          className={`text-xs px-3 py-1 rounded-lg border transition-all font-semibold flex items-center space-x-1.5 ${
            isRecording
              ? 'border-red-500 text-white bg-red-600 animate-pulse shadow-md shadow-red-600/30'
              : 'border-emerald-500/60 text-white bg-emerald-600 hover:bg-emerald-500 shadow-sm'
          }`}
          title="Click to speak command or press Ctrl+Shift+V"
        >
          <span>🎙️</span>
          <span>{isRecording ? 'Listening...' : 'Speak Command'}</span>
        </button>

        {/* QUICK BILL GENERATOR BUTTON */}
        <button
          onClick={onOpenBill}
          className="text-xs px-3 py-1 rounded-lg border border-gray-700 text-gray-200 bg-gray-900 hover:bg-gray-800 hover:border-gray-600 font-semibold flex items-center space-x-1.5 transition-all"
          title="Create or print commercial Kirana cash memo"
        >
          <span>🧾</span>
          <span>Bill</span>
        </button>

        {/* PHONE CALL SIMULATOR */}
        <button
          onClick={onOpenSimulator}
          className="text-xs px-3 py-1 rounded-lg border border-violet-500/40 text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 font-semibold flex items-center space-x-1.5 transition-all"
          title="Simulate incoming customer phone call"
        >
          <span>📞</span>
          <span>Call Sim</span>
        </button>

        {/* STORE FEEDBACK BUTTON */}
        <button
          onClick={onOpenFeedback}
          className="text-xs px-3 py-1 rounded-lg border border-amber-500/40 text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 font-semibold flex items-center space-x-1.5 transition-all"
          title="Leave store manager feedback or report issue"
        >
          <span>💬</span>
          <span>Feedback</span>
        </button>
      </div>

      {/* WINDOW CONTROLS */}
      <div className="window-controls flex space-x-1.5">
        <button
          className="control-btn minimize w-7 h-7 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white text-sm"
          onClick={handleMinimize}
          title="Minimize"
        >
          &minus;
        </button>
        <button
          className="control-btn close w-7 h-7 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-red-600 text-gray-400 hover:text-white text-sm"
          onClick={handleClose}
          title="Close"
        >
          &times;
        </button>
      </div>
    </header>
  );
}
