import { INDIAN_LANGUAGES } from '../constants/languages';

export default function Header({
  selectedLangCode,
  setSelectedLangCode,
  isMuted,
  setIsMuted,
  isRecording,
  startRecording,
  onOpenSimulator,
  handleMinimize,
  handleClose,
}) {
  return (
    <header className="overlay-header absolute top-0 left-0 w-full flex justify-between items-center px-4 py-2 bg-gray-900/90 backdrop-blur-md border-b border-gray-700 pointer-events-auto z-50">
      <div className="flex items-center space-x-2">
        <span className="text-xs font-bold text-gray-400 tracking-wider">KIRANASYNC</span>
        <select
          value={selectedLangCode}
          onChange={(e) => setSelectedLangCode(e.target.value)}
          className="bg-gray-800 text-gray-200 text-xs px-2 py-0.5 rounded border border-gray-600 focus:outline-none focus:border-indigo-400 cursor-pointer"
          title="Select Spoken Language"
        >
          {INDIAN_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
        <button
          onClick={() => setIsMuted(!isMuted)}
          className={`text-xs px-2 py-0.5 rounded border ${
            isMuted
              ? 'border-red-500/50 text-red-400 bg-red-500/10'
              : 'border-emerald-500/50 text-emerald-400 bg-emerald-500/10'
          }`}
          title={isMuted ? 'Audio feedback is muted' : 'Audio feedback is active (Gnani Timbre)'}
        >
          {isMuted ? '🔇 Muted' : '🔊 Voice ON'}
        </button>
        <button
          onClick={startRecording}
          className={`text-xs px-2.5 py-0.5 rounded border transition-all font-semibold flex items-center space-x-1 ${
            isRecording
              ? 'border-red-500 text-white bg-red-600 animate-pulse'
              : 'border-indigo-500/60 text-indigo-300 bg-indigo-500/20 hover:bg-indigo-500/30'
          }`}
          title="Click to speak command or press Ctrl+Shift+V"
        >
          <span>🎙️</span>
          <span>{isRecording ? 'Listening...' : 'Speak'}</span>
        </button>
        <button
          onClick={onOpenSimulator}
          className="text-xs px-2.5 py-0.5 rounded border border-emerald-500/60 text-emerald-300 bg-emerald-500/20 hover:bg-emerald-500/30 font-semibold flex items-center space-x-1"
          title="Simulate phone call"
        >
          <span>📞</span>
          <span>Call</span>
        </button>
      </div>
      <div className="window-controls flex space-x-1">
        <button className="control-btn minimize" onClick={handleMinimize} title="Minimize">
          &minus;
        </button>
        <button className="control-btn close" onClick={handleClose} title="Close">
          &times;
        </button>
      </div>
    </header>
  );
}
