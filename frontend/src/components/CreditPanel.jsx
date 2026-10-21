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
  handleEditCustomer,
  onRequestRemoval,
  onDirectArchive,
}) {
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-rose-400">{t.credTitle}</h3>
        <button
          onClick={() => setShowAddCust(!showAddCust)}
          className="text-sm bg-rose-500/20 text-rose-400 px-3 py-1 rounded hover:bg-rose-500/40"
        >
          {t.addBtn}
        </button>
      </div>

      {showAddCust && (
        <form
          onSubmit={handleAddCustomer}
          className="bg-gray-800 p-4 rounded-xl mb-4 border border-gray-700 flex flex-col space-y-2"
        >
          <input
            required
            type="text"
            placeholder={t.custPlace}
            className="bg-gray-700 text-white p-2 rounded"
            value={custForm.CustomerName}
            onChange={(e) => setCustForm({ ...custForm, CustomerName: e.target.value })}
          />
          <input
            required
            type="number"
            min="0"
            placeholder={t.balPlace}
            className="bg-gray-700 text-white p-2 rounded"
            value={custForm.Amount}
            onChange={(e) => setCustForm({ ...custForm, Amount: e.target.value })}
          />
          {manualFormError && (
            <p role="alert" className="text-sm text-red-400">
              {manualFormError}
            </p>
          )}
          <button type="submit" className="bg-rose-500 text-white py-2 rounded font-semibold mt-2">
            {t.saveCust}
          </button>
        </form>
      )}

      <div className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-gray-700/50 text-gray-400 uppercase">
            <tr>
              <th className="px-4 py-3">{t.thCust}</th>
              <th className="px-4 py-3">{t.thBal}</th>
              <th className="px-4 py-3 text-right">{t.thAction}</th>
            </tr>
          </thead>
          <tbody>
            {credit.map((person) => (
              <tr key={person.CustomerID} className="border-b border-gray-700/50">
                <td className="px-4 py-3 font-medium text-white">
                  {editCustId === person.CustomerID ? (
                    <input
                      type="text"
                      className="bg-gray-700 text-white p-1 rounded text-sm w-full"
                      value={editCustName}
                      onChange={(e) => setEditCustName(e.target.value)}
                      autoFocus
                    />
                  ) : (
                    person.CustomerName
                  )}
                </td>
                <td className="px-4 py-3 text-rose-400 font-semibold">
                  ₹{person.OutstandingBalance}
                </td>
                <td className="px-4 py-3 text-right">
                  {editCustId === person.CustomerID ? (
                    <button
                      onClick={() => handleEditCustomer(person.CustomerID)}
                      className="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1 bg-emerald-500/20 rounded ml-2"
                    >
                      {t.saveBtn}
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setEditCustId(person.CustomerID);
                          setEditCustName(person.CustomerName);
                        }}
                        className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-700 rounded ml-2"
                      >
                        {t.editBtn}
                      </button>
                      <button
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
