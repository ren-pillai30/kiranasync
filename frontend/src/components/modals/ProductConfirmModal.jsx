import { motion, AnimatePresence } from 'framer-motion';

export default function ProductConfirmModal({
  pendingDraft,
  setPendingDraft,
  confirmationError,
  setConfirmationError,
  isSearchingProduct,
  manualMrp,
  setManualMrp,
  searchEditedProductName,
  addManualMrp,
  submitConfirmation,
  onCancel,
  t,
}) {
  return (
    <AnimatePresence>
      {pendingDraft && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto"
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            className="bg-gray-800 border border-blue-500/50 p-6 rounded-2xl shadow-2xl w-[400px] max-h-[85vh] overflow-y-auto"
          >
            <div className="flex items-center space-x-3 mb-2">
              <span className="text-2xl">🔍</span>
              <h3 className="text-xl font-bold text-white">{t.confirmTitle}</h3>
            </div>
            <p className="text-gray-400 text-sm mb-6">{t.confirmDesc}</p>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 font-semibold uppercase">{t.thItem}</label>
                <input
                  type="text"
                  className="w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600 focus:border-blue-500 outline-none"
                  value={pendingDraft.ItemName}
                  onChange={(e) => {
                    setPendingDraft({
                      ...pendingDraft,
                      ItemName: e.target.value,
                      Price: null,
                      PriceFound: false,
                      PriceIsMRP: false,
                      SearchStatus: 'not_searched',
                      SearchResults: [],
                      PriceOptions: [],
                    });
                    setConfirmationError('');
                  }}
                />
                <button
                  type="button"
                  onClick={searchEditedProductName}
                  disabled={!pendingDraft.ItemName.trim() || isSearchingProduct}
                  className="mt-2 px-3 py-2 rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 disabled:opacity-40 text-sm"
                >
                  {isSearchingProduct ? t.searching : t.searchAgain}
                </button>
                <p className="text-xs text-gray-500 mt-1">{t.editNameToSearch}</p>
              </div>
              <div className="flex space-x-4">
                <p className="text-xs text-gray-500 font-semibold uppercase">{t.mrpOptions}</p>
              </div>
              <p className="text-sm text-gray-300">
                {pendingDraft.SearchStatus === 'searching'
                  ? t.searching
                  : pendingDraft.PriceIsMRP
                  ? t.searchFound
                  : pendingDraft.PriceFound
                  ? t.searchPriceOnly
                  : ['error', 'unavailable'].includes(pendingDraft.SearchStatus)
                  ? t.searchError
                  : pendingDraft.SearchStatus === 'no_relevant_results'
                  ? pendingDraft.SearchMessage
                  : t.lookupUnavailable}
              </p>
              <p className="text-xs text-gray-400">{t.productVariantNote}</p>
              {pendingDraft.PriceOptions?.length > 0 ? (
                <div className="space-y-3">
                  {pendingDraft.PriceOptions.map((option, index) => (
                    <div
                      key={`${option.Price}-${index}`}
                      className={`block p-3 rounded-xl border ${
                        option.Selected
                          ? 'border-blue-500 bg-blue-500/10'
                          : 'border-gray-700 bg-gray-700/40'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={Boolean(option.Selected)}
                          aria-label={`${t.chooseMrp} ₹${option.Price}`}
                          onChange={(event) =>
                            setPendingDraft((current) => ({
                              ...current,
                              PriceOptions: current.PriceOptions.map((entry, entryIndex) =>
                                entryIndex === index
                                  ? { ...entry, Selected: event.target.checked }
                                  : entry
                              ),
                            }))
                          }
                          className="mt-1 accent-blue-500"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-center">
                            <span className="font-semibold text-white">
                              ₹{Number(option.Price).toLocaleString('en-IN')}
                              {option.IsManual
                                ? ` · ${t.manualMrp}`
                                : option.PriceIsMRP
                                ? ' · MRP'
                                : ' · online price'}
                            </span>
                            <span className="text-xs text-gray-400">
                              {t.purchaseTotal}: ₹
                              {(
                                Number(option.Price) * Number(option.Quantity)
                              ).toLocaleString('en-IN')}
                            </span>
                          </div>
                          <div className="mt-2">
                            <label className="text-xs text-gray-400">{t.quantityForMrp}</label>
                            <input
                              type="number"
                              min="1"
                              step="1"
                              value={option.Quantity}
                              onChange={(event) =>
                                setPendingDraft((current) => ({
                                  ...current,
                                  PriceOptions: current.PriceOptions.map((entry, entryIndex) =>
                                    entryIndex === index
                                      ? { ...entry, Quantity: event.target.value }
                                      : entry
                                  ),
                                }))
                              }
                              onClick={(event) => event.stopPropagation()}
                              className="block w-full bg-gray-700 text-white p-2 rounded-lg mt-1 border border-gray-600"
                            />
                          </div>
                          {option.Sources?.length > 0 && (
                            <p className="text-xs text-gray-500 mt-2">{t.mrpSources}</p>
                          )}
                          {option.Sources?.map((source, sourceIndex) => (
                            <div key={`${source.URL}-${sourceIndex}`} className="mt-2 text-xs">
                              {source.URL ? (
                                <a
                                  href={source.URL}
                                  target="_blank"
                                  rel="noreferrer"
                                  onClick={(event) => event.stopPropagation()}
                                  className="text-blue-400 underline"
                                >
                                  {source.Title || source.URL}
                                </a>
                              ) : (
                                <span className="text-gray-300">{source.Title}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">{t.noPriceOptions}</p>
              )}
              <div className="border-t border-gray-700 pt-3">
                <label className="text-xs text-gray-400">{t.addAnotherMrp}</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={manualMrp}
                    onChange={(event) => setManualMrp(event.target.value)}
                    placeholder={t.mrpPlace}
                    className="flex-1 min-w-0 bg-gray-700 text-white p-2 rounded-lg border border-gray-600"
                  />
                  <button
                    type="button"
                    onClick={addManualMrp}
                    disabled={!(Number(manualMrp) > 0)}
                    className="px-3 rounded-lg bg-blue-500/20 text-blue-300 disabled:opacity-40"
                  >
                    {t.addMrp}
                  </button>
                </div>
              </div>
              {pendingDraft.PriceOptions?.length === 0 &&
                pendingDraft.SearchResults?.length > 0 && (
                  <div className="border-t border-gray-700 pt-3">
                    <p className="text-xs text-gray-400 font-semibold uppercase mb-2">
                      {t.sourceLabel}
                    </p>
                    <ul className="space-y-2">
                      {pendingDraft.SearchResults.map((source, index) => (
                        <li key={`${source.URL}-${index}`} className="text-xs">
                          {source.URL ? (
                            <a
                              href={source.URL}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-400 hover:text-blue-300 underline"
                            >
                              {source.Title || source.URL}
                            </a>
                          ) : (
                            <span className="text-gray-300">{source.Title}</span>
                          )}
                          {source.Snippet && <p className="text-gray-500 mt-1">{source.Snippet}</p>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {confirmationError && (
                <p role="alert" className="text-sm text-red-400">
                  {confirmationError}
                </p>
              )}
            </div>

            <div className="mt-8 flex space-x-3">
              <button
                onClick={onCancel}
                className="w-1/3 py-3 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium transition-colors"
              >
                {t.cancelBtn}
              </button>
              <button
                onClick={submitConfirmation}
                disabled={
                  !pendingDraft.ItemName.trim() ||
                  isSearchingProduct ||
                  !pendingDraft.PriceOptions?.some(
                    (option) =>
                      option.Selected &&
                      Number(option.Quantity) > 0 &&
                      Number.isInteger(Number(option.Quantity))
                  )
                }
                className="w-2/3 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold shadow-lg shadow-blue-500/20 transition-all"
              >
                {t.confirmAddBtn}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
