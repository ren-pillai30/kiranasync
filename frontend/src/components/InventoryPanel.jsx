export default function InventoryPanel({
  inventory,
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
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-blue-400">{t.invTitle}</h3>
        <button
          onClick={() => setShowAddInv(!showAddInv)}
          className="text-sm bg-blue-500/20 text-blue-400 px-3 py-1 rounded hover:bg-blue-500/40"
        >
          {t.addBtn}
        </button>
      </div>

      {showAddInv && (
        <form
          onSubmit={handleAddInventory}
          className="bg-gray-800 p-4 rounded-xl mb-4 border border-gray-700 flex flex-col space-y-2"
        >
          <input
            required
            type="text"
            placeholder={t.itemPlace}
            className="bg-gray-700 text-white p-2 rounded"
            value={invForm.ItemName}
            onChange={(e) => setInvForm({ ...invForm, ItemName: e.target.value })}
          />
          <div className="flex space-x-2">
            <input
              required
              type="number"
              placeholder={t.qtyPlace}
              className="bg-gray-700 text-white p-2 rounded w-1/2"
              value={invForm.StockQuantity}
              onChange={(e) => setInvForm({ ...invForm, StockQuantity: e.target.value })}
            />
            <input
              required
              type="number"
              placeholder={t.pricePlace}
              className="bg-gray-700 text-white p-2 rounded w-1/2"
              value={invForm.Price}
              onChange={(e) => setInvForm({ ...invForm, Price: e.target.value })}
            />
          </div>
          {manualFormError && (
            <p role="alert" className="text-sm text-red-400">
              {manualFormError}
            </p>
          )}
          <button type="submit" className="bg-blue-500 text-white py-2 rounded font-semibold mt-2">
            {t.saveItem}
          </button>
        </form>
      )}

      <div className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-gray-700/50 text-gray-400 uppercase">
            <tr>
              <th className="px-4 py-3">{t.thItem}</th>
              <th className="px-4 py-3">{t.thStock}</th>
              <th className="px-4 py-3">{t.thPrice}</th>
              <th className="px-4 py-3 text-right">{t.thAction}</th>
            </tr>
          </thead>
          <tbody>
            {inventory.map((item) => (
              <tr key={item.ItemID} className="border-b border-gray-700/50">
                <td className="px-4 py-3 font-medium text-white">
                  {editInvId === item.ItemID ? (
                    <input
                      type="text"
                      className="bg-gray-700 text-white p-1 rounded text-sm w-full"
                      value={editInvName}
                      onChange={(e) => setEditInvName(e.target.value)}
                      autoFocus
                    />
                  ) : (
                    item.ItemName
                  )}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded-md ${
                      item.StockQuantity < 10
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-emerald-500/20 text-emerald-400'
                    }`}
                  >
                    {item.StockQuantity}
                  </span>
                </td>
                <td className="px-4 py-3">₹{item.Price}</td>
                <td className="px-4 py-3 text-right">
                  {editInvId === item.ItemID ? (
                    <button
                      onClick={() => handleEditInventory(item.ItemID)}
                      className="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1 bg-emerald-500/20 rounded ml-2"
                    >
                      {t.saveBtn}
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setEditInvId(item.ItemID);
                          setEditInvName(item.ItemName);
                        }}
                        className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-700 rounded ml-2"
                      >
                        {t.editBtn}
                      </button>
                      <button
                        onClick={() =>
                          onRequestRemoval({
                            EntityType: 'Product',
                            EntityID: item.ItemID,
                            EntityName: item.ItemName,
                            QuantityOrBalance: item.StockQuantity,
                            Reason: '',
                          })
                        }
                        className="text-red-300 hover:text-red-200 text-xs px-2 py-1 bg-red-500/20 rounded ml-2"
                      >
                        Remove
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

