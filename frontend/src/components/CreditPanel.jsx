function EntityName({ english, hindi, mode }) {
  const hasHindi = Boolean(hindi?.trim());
  if (mode === 'hi') return <>{hasHindi ? hindi : english}</>;
  if (mode === 'both') {
    return (
      <span className="flex flex-col">
        <span>{english}</span>
        {hasHindi && <span className="text-xs text-stone-500">{hindi}</span>}
      </span>
    );
  }
  return <>{english}</>;
}

export default function CreditPanel({
  credit,
  t,
  showAddCust,
  setShowAddCust,
  custForm,
  setCustForm,
  manualFormError,
  handleAddCustomer,
  editCustId,
  setEditCustId,
  editCustName,
  setEditCustName,
  editCustNameHindi,
  setEditCustNameHindi,
  handleEditCustomer,
  nameDisplayMode,
  onRequestRemoval,
  onDirectArchive,
}) {
  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center space-x-2">
          <h3 className="text-base font-bold text-stone-900 flex items-center space-x-1.5">
            <span>{t.credTitle}</span>
          </h3>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-red-100 text-red-900 border border-red-200 font-bold">
            {credit.length} Khata
          </span>
        </div>
        <button
          onClick={() => setShowAddCust(!showAddCust)}
          className="text-xs bg-[#991B1B] hover:bg-[#B91C1C] text-[#FFFDF7] px-3 py-1.5 rounded-lg font-bold shadow-xs flex items-center space-x-1 transition-all"
        >
          <span>{showAddCust ? '' : '+'}</span>
          <span>{t.addBtn}</span>
        </button>
      </div>

      {showAddCust && (
        <form
          onSubmit={handleAddCustomer}
          className="bg-[#FBF9F4] p-4 rounded-xl mb-4 border border-[#E2D9C8] flex flex-col space-y-2.5 shadow-sm animate-in fade-in duration-200"
        >
          <div className="text-xs font-bold uppercase text-[#78716C] tracking-wider mb-1">
            New Customer Khata
          </div>
          <input
            required
            type="text"
            placeholder={t.custPlace}
            className="bg-[#FFFDF9] text-stone-900 placeholder:text-stone-400 p-2.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] text-sm font-medium transition-all"
            value={custForm.CustomerName}
            onChange={(e) => setCustForm({ ...custForm, CustomerName: e.target.value })}
          />
          <input
            type="text"
            placeholder="Hindi customer name (optional)"
            className="bg-[#FFFDF9] text-stone-900 placeholder:text-stone-400 p-2.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] text-sm font-medium transition-all"
            value={custForm.CustomerNameHindi}
            onChange={(e) => setCustForm({ ...custForm, CustomerNameHindi: e.target.value })}
          />
          <input
            required
            type="number"
            min="0"
            placeholder={t.balPlace}
            className="bg-[#FFFDF9] text-stone-900 placeholder:text-stone-400 p-2.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] text-sm font-medium transition-all"
            value={custForm.Amount}
            onChange={(e) => setCustForm({ ...custForm, Amount: e.target.value })}
          />
          {manualFormError && (
            <p role="alert" className="text-xs text-red-600 font-semibold bg-red-50 p-2 rounded border border-red-200">
              {manualFormError}
            </p>
          )}
          <button
            type="submit"
            className="bg-[#991B1B] hover:bg-[#B91C1C] text-[#FFFDF7] py-2 rounded-lg font-bold text-sm shadow-xs transition-all"
          >
            {t.saveCust}
          </button>
        </form>
      )}

      <div className="bg-[#FFFDF9] rounded-xl overflow-auto max-h-72 border border-[#E2D9C8] shadow-xs custom-scrollbar">
        <table className="w-full min-w-[420px] text-left text-sm text-stone-700">
          <thead className="bg-[#F4EFE6] text-[#57534E] uppercase text-[11px] tracking-wider font-bold border-b border-[#E2D9C8] sticky top-0 z-10">
            <tr>
              <th className="px-4 py-2.5">{t.thCust}</th>
              <th className="px-4 py-2.5">{t.thBal}</th>
              <th className="px-4 py-2.5 text-right">{t.thAction}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F0EAE0]">
            {credit.length === 0 ? (
              <tr>
                <td colSpan="3" className="px-4 py-6 text-center text-[#78716C] italic text-xs">
                  No active customer credit accounts found.
                </td>
              </tr>
            ) : (
              credit.map((person) => (
                <tr key={person.CustomerID} className="hover:bg-[#FAF6EE] transition-colors">
                  <td className="px-4 py-2.5 font-semibold text-stone-900">
                    {editCustId === person.CustomerID ? (
                      <div className="space-y-1">
                        <input
                          type="text"
                          aria-label="English customer name"
                          className="bg-[#FFFDF9] text-stone-900 p-1.5 rounded border border-[#991B1B] text-sm w-full font-medium focus:outline-none"
                          value={editCustName}
                          onChange={(e) => setEditCustName(e.target.value)}
                          autoFocus
                        />
                        <input
                          type="text"
                          aria-label="Hindi customer name"
                          className="bg-[#FFFDF9] text-stone-900 p-1.5 rounded border border-[#D8CEBA] text-sm w-full font-medium focus:outline-none"
                          value={editCustNameHindi}
                          onChange={(e) => setEditCustNameHindi(e.target.value)}
                        />
                      </div>
                    ) : (
                      <EntityName english={person.CustomerName} hindi={person.CustomerNameHindi} mode={nameDisplayMode} />
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-[#DC2626] font-mono font-bold">
                    ₹{Number(person.OutstandingBalance).toLocaleString('en-IN')}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {editCustId === person.CustomerID ? (
                      <button
                        type="button"
                        onClick={() => handleEditCustomer(person.CustomerID)}
                        className="text-white bg-[#991B1B] hover:bg-[#B91C1C] text-xs px-3 py-1.5 rounded-md font-bold shadow-xs transition-all cursor-pointer"
                      >
                        {t.saveBtn}
                      </button>
                    ) : (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setEditCustId(person.CustomerID);
                            setEditCustName(person.CustomerName);
                            setEditCustNameHindi(person.CustomerNameHindi || '');
                          }}
                          className="text-stone-700 hover:text-stone-900 text-xs px-3 py-1 bg-[#F4EFE6] hover:bg-[#EAE2D2] border border-[#D8CEBA] rounded-md font-semibold transition-all shadow-2xs cursor-pointer"
                        >
                          {t.editBtn}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            const removal = {
                              EntityType: 'Customer',
                              EntityID: person.CustomerID,
                              EntityName: person.CustomerName,
                              QuantityOrBalance: person.OutstandingBalance,
                              Reason: '',
                            };
                            if (Number(person.OutstandingBalance) < 1) {
                              onDirectArchive(removal);
                            } else {
                              onRequestRemoval(removal);
                            }
                          }}
                          className="text-red-700 hover:text-red-900 text-xs px-3 py-1 bg-red-50 hover:bg-red-100 border border-red-200 rounded-md font-semibold transition-all shadow-2xs cursor-pointer"
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
