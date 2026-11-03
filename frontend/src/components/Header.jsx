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
  onOpenDayClosing,
  onOpenBarcode,
  handleMinimize,
  handleClose,
}) {
  return (
    <header className="overlay-header absolute top-0 left-0 w-full flex justify-between items-center px-5 py-2.5 bg-[#991B1B] border-b border-[#7F1D1D] pointer-events-auto z-50 shadow-md select-none">
      {/* BRAND & POS COUNTER BADGE */}
      <div className="flex items-center gap-3.5 flex-wrap">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-black text-[#FFFDF7] tracking-wider uppercase drop-shadow-xs">
            KIRANA<span className="text-[#FEF3C7]">SYNC</span>
          </span>
        </div>

        <div className="h-4 w-px bg-red-800"></div>

        {/* LANGUAGE SELECT */}
        <select
          value={selectedLangCode}
          onChange={(e) => setSelectedLangCode(e.target.value)}
          className="bg-[#FFFDF7] text-stone-800 text-xs px-3 py-1.5 rounded-lg border border-[#FDE68A] focus:outline-none focus:ring-2 focus:ring-[#FEF3C7] cursor-pointer font-semibold shadow-xs hover:border-amber-400 transition-all"
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
          type="button"
          onClick={() => setIsMuted(!isMuted)}
          className={`text-xs px-3 py-1.5 rounded-lg border font-semibold transition-all shadow-xs cursor-pointer ${
            isMuted
              ? 'border-red-300 text-red-950 bg-red-100 hover:bg-red-200'
              : 'border-[#FDE68A] text-[#78350F] bg-[#FEF3C7] hover:bg-[#FDE68A]'
          }`}
          title={isMuted ? 'Audio feedback is muted' : 'Audio feedback is active (Gnani Timbre)'}
        >
          {isMuted ? ' Audio Muted' : ' Voice Output ON'}
        </button>

        {/* VOICE COMMAND BUTTON */}
        <button
          type="button"
          onClick={startRecording}
          className={`text-xs px-3.5 py-1.5 rounded-lg border transition-all font-bold flex items-center space-x-1.5 shadow-sm cursor-pointer ${
            isRecording
              ? 'border-red-400 text-white bg-red-600 animate-pulse shadow-md shadow-red-900/50'
              : 'border-[#FDE68A] text-[#78350F] bg-[#FEF3C7] hover:bg-[#FDE68A] hover:border-amber-400'
          }`}
          title="Click to speak command or press Ctrl+Shift+V"
        >
          <span className="text-[10px] font-black uppercase">Mic</span>
          <span>{isRecording ? 'Listening...' : 'Speak Command'}</span>
        </button>

        {/* QUICK BILL GENERATOR BUTTON */}
        <button
          type="button"
          onClick={onOpenBill}
          className="text-xs px-3.5 py-1.5 rounded-lg border border-[#E2D9C8] text-stone-800 bg-[#FFFDF7] hover:bg-[#F4EFE6] hover:border-stone-400 font-semibold flex items-center space-x-1.5 shadow-xs transition-all cursor-pointer"
          title="Create or print commercial Kirana cash memo"
        >
          <span className="text-[10px] font-black uppercase">Bill</span>
          <span>Bill</span>
        </button>

        {/* PHONE CALL SIMULATOR */}
        <button
          type="button"
          onClick={onOpenSimulator}
          className="text-xs px-3.5 py-1.5 rounded-lg border border-red-300/80 text-red-950 bg-red-100 hover:bg-red-200 hover:border-red-400 font-semibold flex items-center space-x-1.5 shadow-xs transition-all cursor-pointer"
          title="Simulate incoming customer phone call"
        >
          <span className="text-[10px] font-black uppercase">Call</span>
          <span>Call Sim</span>
        </button>

        {/* BARCODE SCANNER BUTTON */}
        <button
          type="button"
          onClick={onOpenBarcode}
          className="text-xs px-3.5 py-1.5 rounded-lg border border-[#FDE68A] text-stone-900 bg-[#FFFDF7] hover:bg-[#FEF3C7] font-semibold flex items-center space-x-1.5 shadow-xs transition-all cursor-pointer"
          title="Scan or lookup product barcode"
        >
          <span className="text-[10px] font-black uppercase">Scan</span>
          <span>Barcode</span>
        </button>

        {/* DAY CLOSING (DUKAN BANDI) */}
        <button
          type="button"
          onClick={onOpenDayClosing}
          className="text-xs px-3.5 py-1.5 rounded-lg border border-[#FDE68A] text-stone-900 bg-[#FFFDF7] hover:bg-[#FEF3C7] font-semibold flex items-center space-x-1.5 shadow-xs transition-all cursor-pointer"
          title="Evening cash drawer tally & dukan bandi"
        >
          <span className="text-[10px] font-black uppercase">Close</span>
          <span>Day Closing</span>
        </button>

        {/* STORE FEEDBACK BUTTON */}
        <button
          type="button"
          onClick={onOpenFeedback}
          className="text-xs px-3.5 py-1.5 rounded-lg border border-[#FDE68A] text-[#92400E] bg-[#FFFDF7] hover:bg-[#FEF3C7] hover:border-amber-400 font-semibold flex items-center space-x-1.5 shadow-xs transition-all cursor-pointer"
          title="Leave store manager feedback or report issue"
        >
          <span className="text-[10px] font-black uppercase">Help</span>
          <span>Feedback</span>
        </button>
      </div>

      {/* WINDOW CONTROLS */}
      {Boolean(window.pywebview) && <div className="window-controls flex items-center space-x-2 pl-3">
        <button
          type="button"
          className="control-btn minimize w-7 h-7 flex items-center justify-center rounded-lg bg-red-900/80 hover:bg-red-800 text-red-100 hover:text-white text-sm font-bold shadow-xs transition-all cursor-pointer"
          onClick={handleMinimize}
          title="Minimize"
        >
          &minus;
        </button>
        <button
          type="button"
          className="control-btn close w-7 h-7 flex items-center justify-center rounded-lg bg-red-900/80 hover:bg-red-600 text-red-100 hover:text-white text-sm font-bold shadow-xs transition-all cursor-pointer"
          onClick={handleClose}
          title="Close"
        >
          &times;
        </button>
      </div>}
    </header>
  );
}
