import { motion } from 'framer-motion';
import HisaabBanner from './HisaabBanner';
import InventoryPanel from './InventoryPanel';
import CreditPanel from './CreditPanel';
import TransactionLedger from './TransactionLedger';

export default function DashboardView({
  t,
  lang,
  setLang,
  onOpenBarcode,
  onOpenDayClosing,
  onOpenEvalModal,
  onOpenArchives,
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
          </div>
          <span className="text-xs text-[#991B1B] font-mono font-semibold tracking-wide flex items-center space-x-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#991B1B] animate-pulse"></span>
            <span>Sovereign Voice Engine 2.0 (Gnani Prisma &amp; Timbre)</span>
          </span>
        </div>
        <div className="flex items-center gap-2.5 flex-wrap">
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
            onClick={onOpenBarcode}
            className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 border border-[#D8CEBA] rounded-lg text-xs font-bold shadow-2xs transition-all flex items-center space-x-1.5 cursor-pointer"
            title="Scan or lookup product barcode"
          >
            <span>📷</span>
            <span>Barcode</span>
          </button>

          <button
            type="button"
            onClick={onOpenDayClosing}
            className="px-3.5 py-1.5 bg-[#991B1B] hover:bg-[#B91C1C] text-white border border-[#991B1B] rounded-lg text-xs font-bold shadow-2xs transition-all flex items-center space-x-1.5 cursor-pointer"
            title="Evening cash drawer tally and dukan bandi"
          >
            <span>🌙</span>
            <span>{lang === 'hi' ? 'दुकान बंदी' : 'Day Closing'}</span>
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
