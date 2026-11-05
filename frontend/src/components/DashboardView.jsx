import { motion } from 'framer-motion';
import HisaabBanner from './HisaabBanner';
import InventoryPanel from './InventoryPanel';
import CreditPanel from './CreditPanel';
import TransactionLedger from './TransactionLedger';

export default function DashboardView({
  t,
  lang,
  onLanguageChange,
  onOpenArchives,
  onViewBill,
  hisaabData,
  inventory,
  dashboardLoading,
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
  editInvNameHindi,
  setEditInvNameHindi,
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
  editCustNameHindi,
  setEditCustNameHindi,
  handleEditCustomer,
  onDirectArchive,
  transactions,
  nameDisplayMode,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="w-full max-w-5xl bg-[#FAF7F2] border border-[#DFD5C3] rounded-xl sm:rounded-2xl p-3 sm:p-7 shadow-[0_20px_50px_rgba(28,25,23,0.18)] pointer-events-auto max-h-[calc(100dvh-90px)] overflow-y-auto text-stone-900 select-none"
    >
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-5 pb-4 border-b border-[#E2D9C8]">
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
          <div className="flex rounded-lg border border-[#D8CEBA] bg-[#FFFDF9] p-0.5" aria-label="Entity name language">
            {[
              ['en', 'EN'],
              ['hi', 'हिंदी'],
            ].map(([mode, label]) => (
              <button
                key={mode}
                type="button"
                onClick={() => onLanguageChange(mode)}
                className={`px-2 py-1 rounded-md text-[11px] font-bold transition-colors ${nameDisplayMode === mode ? 'bg-[#991B1B] text-white' : 'text-stone-600 hover:bg-[#F4EFE6]'}`}
              >
                {label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={onOpenArchives}
            className="px-3.5 py-1.5 bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 border border-[#D8CEBA] rounded-lg text-xs font-bold shadow-2xs transition-all cursor-pointer"
          >
            {lang === 'hi' ? 'आर्काइव' : 'Archives'}
          </button>

        </div>
      </div>

      {/* QUICK HISAAB SUMMARY BANNER */}
      <HisaabBanner hisaabData={hisaabData} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        {/* INVENTORY PANEL */}
        <InventoryPanel
          inventory={inventory}
          loading={dashboardLoading}
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
          editInvNameHindi={editInvNameHindi}
          setEditInvNameHindi={setEditInvNameHindi}
          handleEditInventory={handleEditInventory}
          onRequestRemoval={onRequestRemoval}
          nameDisplayMode={nameDisplayMode}
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
          editCustNameHindi={editCustNameHindi}
          setEditCustNameHindi={setEditCustNameHindi}
          handleEditCustomer={handleEditCustomer}
          onRequestRemoval={onRequestRemoval}
          onDirectArchive={onDirectArchive}
          nameDisplayMode={nameDisplayMode}
        />
      </div>

      {/* TRANSACTION LEDGER */}
      <TransactionLedger transactions={transactions} t={t} onViewBill={onViewBill} />
    </motion.div>
  );
}
