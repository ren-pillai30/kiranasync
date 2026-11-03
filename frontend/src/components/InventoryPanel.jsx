export default function InventoryPanel({
  inventory,
  loading,
  t,
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
}) {
  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center space-x-2">
          <h3 className="text-base font-bold text-stone-900 flex items-center space-x-1.5">
            <span className="text-base"></span>
            <span>{t.invTitle}</span>
          </h3>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] font-bold">
            {inventory.length} Items
          </span>
        </div>
        <button
          onClick={() => setShowAddInv(!showAddInv)}
          className="text-xs bg-[#991B1B] hover:bg-[#B91C1C] text-[#FFFDF7] px-3 py-1.5 rounded-lg font-bold shadow-xs flex items-center space-x-1 transition-all"
        >
          <span>{showAddInv ? '' : '+'}</span>
          <span>{t.addBtn}</span>
        </button>
      </div>

      {showAddInv && (
        <form
          onSubmit={handleAddInventory}
          className="bg-[#FBF9F4] p-4 rounded-xl mb-4 border border-[#E2D9C8] flex flex-col space-y-2.5 shadow-sm animate-in fade-in duration-200"
        >
          <div className="text-xs font-bold uppercase text-[#78716C] tracking-wider mb-1">
            New Product Entry
          </div>
          <input
            required
            type="text"
            placeholder={t.itemPlace}
            className="bg-[#FFFDF9] text-stone-900 placeholder:text-stone-400 p-2.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] text-sm font-medium transition-all"
            value={invForm.ItemName}
            onChange={(e) => setInvForm({ ...invForm, ItemName: e.target.value })}
          />
          <div className="flex space-x-2">
            <input
              required
              type="number"
              placeholder={t.qtyPlace}
              className="bg-[#FFFDF9] text-stone-900 placeholder:text-stone-400 p-2.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] text-sm font-medium w-1/2 transition-all"
              value={invForm.StockQuantity}
              onChange={(e) => setInvForm({ ...invForm, StockQuantity: e.target.value })}
            />
            <input
              required
              type="number"
              placeholder={t.pricePlace}
              className="bg-[#FFFDF9] text-stone-900 placeholder:text-stone-400 p-2.5 rounded-lg border border-[#D8CEBA] focus:outline-none focus:ring-2 focus:ring-[#991B1B]/20 focus:border-[#991B1B] text-sm font-medium w-1/2 transition-all"
              value={invForm.Price}
              onChange={(e) => setInvForm({ ...invForm, Price: e.target.value })}
            />
          </div>
          {manualFormError && (
            <p role="alert" className="text-xs text-red-600 font-semibold bg-red-50 p-2 rounded border border-red-200">
              {manualFormError}
            </p>
          )}
          <button
            type="submit"
            className="bg-[#991B1B] hover:bg-[#B91C1C] text-[#FFFDF7] py-2 rounded-lg font-bold text-sm shadow-xs transition-all"
          >
            {t.saveItem}
          </button>
        </form>
      )}

      <div className="bg-[#FFFDF9] rounded-xl overflow-y-auto max-h-72 border border-[#E2D9C8] shadow-xs custom-scrollbar">
        <table className="w-full text-left text-sm text-stone-700">
          <thead className="bg-[#F4EFE6] text-[#57534E] uppercase text-[11px] tracking-wider font-bold border-b border-[#E2D9C8] sticky top-0 z-10">
            <tr>
              <th className="px-4 py-2.5">{t.thItem}</th>
              <th className="px-4 py-2.5">{t.thStock}</th>
              <th className="px-4 py-2.5">{t.thPrice}</th>
              <th className="px-4 py-2.5 text-right">{t.thAction}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F0EAE0]">
            {loading ? (
              <tr>
                <td colSpan="4" className="px-4 py-7">
                  <div className="space-y-3 animate-pulse motion-reduce:animate-none" aria-label="Loading inventory">
                    {[0, 1, 2].map((row) => (
                      <div key={row} className="flex items-center gap-4">
                        <div className="h-3 flex-1 rounded-full bg-stone-200" />
                        <div className="h-3 w-12 rounded-full bg-stone-200" />
                        <div className="h-3 w-16 rounded-full bg-stone-200" />
                      </div>
                    ))}
                  </div>
                </td>
              </tr>
            ) : inventory.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-4 py-6 text-center text-[#78716C] italic text-xs">
                  No inventory items registered. Add one above or via voice command.
                </td>
              </tr>
            ) : (
              inventory.map((item) => (
                <tr key={item.ItemID} className="hover:bg-[#FAF6EE] transition-colors">
                  <td className="px-4 py-2.5 font-semibold text-stone-900">
                    {editInvId === item.ItemID ? (
                      <input
                        type="text"
                        className="bg-[#FFFDF9] text-stone-900 p-1.5 rounded border border-[#991B1B] text-sm w-full font-medium focus:outline-none"
                        value={editInvName}
                        onChange={(e) => setEditInvName(e.target.value)}
                        autoFocus
                      />
                    ) : (
                      item.ItemName
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono">
                    <span
                      className={`px-2 py-0.5 rounded-md text-xs font-bold inline-block ${
                        item.StockQuantity < 10
                          ? 'bg-red-100 text-red-800 border border-red-300'
                          : 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]'
                      }`}
                    >
                      {item.StockQuantity}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-mono font-bold text-stone-900">₹{item.Price}</td>
                  <td className="px-4 py-2.5 text-right">
                    {editInvId === item.ItemID ? (
                      <button
                        type="button"
                        onClick={() => handleEditInventory(item.ItemID)}
                        className="text-white bg-[#991B1B] hover:bg-[#B91C1C] text-xs px-3 py-1.5 rounded-md font-bold shadow-xs transition-all cursor-pointer"
                      >
                        {t.saveBtn}
                      </button>
                    ) : (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setEditInvId(item.ItemID);
                            setEditInvName(item.ItemName);
                          }}
                          className="text-stone-700 hover:text-stone-900 text-xs px-3 py-1 bg-[#F4EFE6] hover:bg-[#EAE2D2] border border-[#D8CEBA] rounded-md font-semibold transition-all shadow-2xs cursor-pointer"
                        >
                          {t.editBtn}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            onRequestRemoval({
                              EntityType: 'Product',
                              EntityID: item.ItemID,
                              EntityName: item.ItemName,
                              QuantityOrBalance: item.StockQuantity,
                              Reason: '',
                            })
                          }
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
