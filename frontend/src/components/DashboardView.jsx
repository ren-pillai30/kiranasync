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
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="w-full max-w-5xl bg-gray-900/95 backdrop-blur-xl border border-gray-700 rounded-2xl p-8 shadow-2xl pointer-events-auto max-h-[85vh] overflow-y-auto"
    >
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">{t.title}</h2>
          <span className="text-xs text-emerald-400 font-mono tracking-wide">
            ● Sovereign Voice Engine 2.0 (Gnani Prisma &amp; Timbre)
          </span>
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={selectedLangCode}
            onChange={(e) => setSelectedLangCode(e.target.value)}
            className="bg-gray-800 text-gray-200 text-xs px-2.5 py-1.5 rounded-lg border border-gray-600 focus:outline-none focus:border-indigo-400 cursor-pointer"
            title="Select Voice Language"
          >
            {INDIAN_LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <button
            onClick={startRecording}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-md ${
              isRecording
                ? 'bg-red-600 text-white animate-pulse border border-red-400'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400/50'
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
            onClick={onOpenEvalModal}
            className="px-3 py-1.5 bg-violet-600/30 hover:bg-violet-600/50 text-violet-300 border border-violet-500/40 rounded-lg text-xs font-semibold"
          >
            🔬 Voice AI Lab
          </button>
          <button
            onClick={onOpenArchives}
            className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-semibold"
          >
            {lang === 'hi' ? 'आर्काइव' : 'Archives'}
          </button>
          <button
            onClick={onOpenSimulator}
            className="px-3 py-1.5 bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/40 rounded-lg text-xs font-semibold flex items-center space-x-1"
            title="Simulate incoming customer phone calls"
          >
            <span>📞</span>
            <span>{lang === 'hi' ? 'कॉल सिमुलेटर' : 'Call Simulator'}</span>
          </button>
          <button
            onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium border border-gray-600 transition-colors"
          >
            {t.toggleLang}
          </button>
        </div>
      </div>

      {/* QUICK HISAAB SUMMARY BANNER */}
      <HisaabBanner hisaabData={hisaabData} />

      <div className="grid grid-cols-2 gap-8">
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
      <TransactionLedger transactions={transactions} t={t} />
    </motion.div>
  );
}

