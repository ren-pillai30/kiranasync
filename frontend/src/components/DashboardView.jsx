import { motion } from 'framer-motion';
import { INDIAN_LANGUAGES } from '../constants/languages';
import HisaabBanner from './HisaabBanner';
import InventoryPanel from './InventoryPanel';
import CreditPanel from './CreditPanel';
import TransactionLedger from './TransactionLedger';

export default function DashboardView({
  t,
  lang,
  setLang,
  selectedLangCode,
  setSelectedLangCode,
  isRecording,
  startRecording,
  onOpenSimulator,
  onOpenEvalModal,
  onOpenArchives,
  onOpenBill,
  onOpenFeedback,
  onViewBill,
  hisaabData,
  inventory,
  showAddInv,
  setShowAddInv,
  invForm,
  setInvForm,
  manualFormError,
  handleAddInventory,
  editInvId,
  setEditInvId,
  editInvName,
  setEditInvName,
  handleEditInventory,
  onRequestRemoval,
  credit,
  showAddCust,
  setShowAddCust,
  custForm,
  setCustForm,
  handleAddCustomer,
  editCustId,
  setEditCustId,
  editCustName,
  setEditCustName,
  handleEditCustomer,
  onDirectArchive,
  transactions,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="w-full max-w-5xl bg-[#FAF7F2] border border-[#DFD5C3] rounded-2xl p-7 shadow-[0_20px_50px_rgba(28,25,23,0.18)] pointer-events-auto max-h-[86vh] overflow-y-auto text-stone-900 select-none"
    >
      <div className="flex justify-between items-center mb-5 pb-4 border-b border-[#E2D9C8]">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-black text-stone-900 tracking-tight">{t.title}</h2>
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]">
              Store POS Terminal
            </span>
          </div>
          <span className="text-xs text-[#991B1B] font-mono font-semibold tracking-wide flex items-center space-x-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#991B1B] animate-pulse"></span>
            <span>Sovereign Voice Engine 2.0 (Gnani Prisma &amp; Timbre)</span>
          </span>
        </div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <select
            value={selectedLangCode}
            onChange={(e) => setSelectedLangCode(e.target.value)}
            className="bg-[#FFFDF9] text-stone-800 text-xs px-3 py-1.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 cursor-pointer font-semibold shadow-2xs transition-all hover:border-stone-400"
            title="Select Voice Language"
          >
            {INDIAN_LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={startRecording}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-all shadow-xs cursor-pointer ${
              isRecording
                ? 'bg-red-600 text-white animate-pulse border border-red-500 shadow-md shadow-red-900/30'
                : 'bg-[#991B1B] hover:bg-[#B91C1C] text-[#FFFDF7] border border-[#7F1D1D]'
            }`}
          >
            <span>🎙️</span>
            <span>
              {isRecording
                ? lang === 'hi'
                  ? 'रोकें और भेजें'
                  : 'Stop & Send'
                : lang === 'hi'
                ? 'वॉयस बोलें'
                : 'Speak Command'}
            </span>
          </button>

          <button
            type="button"
            onClick={onOpenEvalModal}
            className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 border border-[#D8CEBA] rounded-lg text-xs font-bold shadow-2xs transition-all flex items-center space-x-1 cursor-pointer"
          >
            <span>🔬</span>
            <span>Voice Lab</span>
          </button>

          <button
            type="button"
            onClick={onOpenBill}
            className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 border border-[#D8CEBA] rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-2xs transition-all cursor-pointer"
            title="Create commercial Kirana bill"
          >
            <span>🧾</span>
            <span>{lang === 'hi' ? 'बिल बनाएं' : 'Kirana Bill'}</span>
          </button>

          <button
            type="button"
            onClick={onOpenFeedback}
            className="px-3.5 py-1.5 bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] border border-[#FDE68A] rounded-lg text-xs font-bold flex items-center space-x-1.5 shadow-2xs transition-all cursor-pointer"
            title="Provide store feedback"
          >
            <span>💬</span>
            <span>{lang === 'hi' ? 'प्रतिक्रिया' : 'Feedback'}</span>
          </button>

          <button
            type="button"
            onClick={onOpenArchives}
            className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 border border-[#D8CEBA] rounded-lg text-xs font-bold shadow-2xs transition-all cursor-pointer"
          >
            {lang === 'hi' ? 'आर्काइव' : 'Archives'}
          </button>

          <button
            type="button"
            onClick={onOpenSimulator}
            className="px-3.5 py-1.5 bg-red-100 hover:bg-red-200 text-red-950 border border-red-300 rounded-lg text-xs font-bold flex items-center space-x-1 shadow-2xs transition-all cursor-pointer"
            title="Simulate incoming customer phone calls"
          >
            <span>📞</span>
            <span>{lang === 'hi' ? 'कॉल सिमुलेटर' : 'Call Simulator'}</span>
          </button>

          <button
            type="button"
            onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
            className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 rounded-lg text-xs font-bold border border-[#D8CEBA] transition-colors shadow-2xs cursor-pointer"
          >
            {t.toggleLang}
          </button>
        </div>
      </div>

      {/* QUICK HISAAB SUMMARY BANNER */}
      <HisaabBanner hisaabData={hisaabData} />

      <div className="grid grid-cols-2 gap-6">
        {/* INVENTORY PANEL */}
        <InventoryPanel
          inventory={inventory}
          t={t}
          showAddInv={showAddInv}
          setShowAddInv={setShowAddInv}
          invForm={invForm}
          setInvForm={setInvForm}
          manualFormError={manualFormError}
          handleAddInventory={handleAddInventory}
          editInvId={editInvId}
          setEditInvId={setEditInvId}
          editInvName={editInvName}
          setEditInvName={setEditInvName}
          handleEditInventory={handleEditInventory}
          onRequestRemoval={onRequestRemoval}
        />

        {/* CREDIT PANEL */}
        <CreditPanel
          credit={credit}
          t={t}
          showAddCust={showAddCust}
          setShowAddCust={setShowAddCust}
          custForm={custForm}
          setCustForm={setCustForm}
          manualFormError={manualFormError}
          handleAddCustomer={handleAddCustomer}
          editCustId={editCustId}
          setEditCustId={setEditCustId}
          editCustName={editCustName}
          setEditCustName={setEditCustName}
          handleEditCustomer={handleEditCustomer}
          onRequestRemoval={onRequestRemoval}
          onDirectArchive={onDirectArchive}
        />
      </div>

      {/* TRANSACTION LEDGER */}
      <TransactionLedger transactions={transactions} t={t} onViewBill={onViewBill} />
    </motion.div>
  );
}
