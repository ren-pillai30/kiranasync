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
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4 cursor-pointer"
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, y: 16 }}
            animate={{ scale: 1, y: 0 }}
            className="relative bg-[#FAF7F2] border-2 border-[#991B1B] p-6 rounded-2xl shadow-2xl w-[420px] max-h-[85vh] overflow-y-auto custom-scrollbar text-stone-900 cursor-auto pointer-events-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Top Close Button */}
            <button
              type="button"
              onClick={onCancel}
              className="absolute top-3 right-3 text-stone-400 hover:text-stone-900 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded-lg hover:bg-stone-200/60 transition-all cursor-pointer"
              title="Close"
            >
              &times;
            </button>

            <div className="flex items-center space-x-3 mb-2">
              <span className="text-2xl p-1 rounded-lg bg-[#FEF3C7]">🔍</span>
              <h3 className="text-xl font-black text-stone-900">{t.confirmTitle}</h3>
            </div>
            <p className="text-[#78716C] text-xs mb-5 font-medium">{t.confirmDesc}</p>

            <div className="space-y-4">
              <div>
                <label className="text-[11px] text-[#78716C] font-bold uppercase tracking-wider">{t.thItem}</label>
                <input
                  type="text"
                  className="w-full bg-[#FFFDF9] text-stone-900 p-2.5 rounded-xl mt-1 border border-[#D8CEBA] focus:border-[#991B1B] focus:ring-2 focus:ring-[#991B1B]/20 outline-none text-sm font-semibold transition-all"
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
                  className="mt-2 px-3 py-1.5 rounded-lg bg-[#991B1B] hover:bg-[#B91C1C] text-white disabled:opacity-40 text-xs font-bold transition-all shadow-xs"
                >
                  {isSearchingProduct ? t.searching : t.searchAgain}
                </button>
                <p className="text-[11px] text-[#78716C] mt-1 font-medium">{t.editNameToSearch}</p>
              </div>
              <div className="flex space-x-4">
                <p className="text-[11px] text-[#78716C] font-bold uppercase tracking-wider">{t.mrpOptions}</p>
              </div>

              {pendingDraft.SearchStatus === 'measurement_mismatch' && (
                <div className="p-3.5 bg-red-50 border border-red-300 rounded-xl text-red-900 text-xs space-y-1.5 shadow-2xs">
                  <div className="font-bold flex items-center space-x-1.5 text-red-800">
                    <span>⚠️</span>
                    <span>Exact measurement ({pendingDraft.RequestedMeasurement || 'requested'}) not available</span>
                  </div>
                  <p className="text-red-900/90 leading-relaxed font-medium">
                    Other measurements found online: <strong className="text-red-950 font-mono">{pendingDraft.AvailableMeasurements?.join(', ')}</strong>. Verify product packaging before selecting.
                  </p>
                </div>
              )}

              <p className="text-xs text-stone-700 font-semibold">
                {pendingDraft.SearchStatus === 'searching'
                  ? t.searching
                  : pendingDraft.SearchStatus === 'measurement_mismatch'
                  ? t.exactMeasurementMismatch
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
              <p className="text-[11px] text-[#78716C]">{t.productVariantNote}</p>
              {pendingDraft.PriceOptions?.length > 0 ? (
                <div className="space-y-2.5">
                  {pendingDraft.PriceOptions.map((option, index) => (
                    <div
                      key={`${option.Price}-${index}`}
                      className={`block p-3 rounded-xl border transition-all ${
                        option.Selected
                          ? 'border-2 border-[#991B1B] bg-[#FFFDF9] shadow-xs'
                          : 'border border-[#D8CEBA] bg-[#F4EFE6]'
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
                          className="mt-1 accent-[#991B1B]"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-center">
                            <span className="font-bold text-stone-900 flex items-center flex-wrap gap-1.5 text-sm">
                              <span>₹{Number(option.Price).toLocaleString('en-IN')}</span>
                              {option.Measurement && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]">
                                  {option.Measurement}
                                </span>
                              )}
                              <span className="text-xs text-[#78716C] font-normal">
                                {option.IsManual
                                  ? ` · ${t.manualMrp}`
                                  : option.PriceIsMRP
                                  ? ' · MRP'
                                  : ' · online price'}
                              </span>
                            </span>
                            <span className="text-xs text-[#78716C] font-mono font-semibold">
                              {t.purchaseTotal}: ₹
                              {(
                                Number(option.Price) * Number(option.Quantity)
                              ).toLocaleString('en-IN')}
                            </span>
                          </div>
                          <div className="mt-2">
                            <label className="text-[11px] font-semibold text-[#78716C]">{t.quantityForMrp}</label>
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
                              className="block w-full bg-[#FFFDF9] text-stone-900 p-2 rounded-lg mt-1 border border-[#D8CEBA] text-sm font-semibold focus:outline-none focus:border-[#991B1B]"
                            />
                          </div>
                          {option.Sources?.length > 0 && (
                            <p className="text-[11px] font-bold text-[#78716C] mt-2">{t.mrpSources}</p>
                          )}
                          {option.Sources?.map((source, sourceIndex) => (
                            <div key={`${source.URL}-${sourceIndex}`} className="mt-1 text-xs">
                              {source.URL ? (
                                <a
                                  href={source.URL}
                                  target="_blank"
                                  rel="noreferrer"
                                  onClick={(event) => event.stopPropagation()}
                                  className="text-[#991B1B] hover:underline font-semibold"
                                >
                                  {source.Title || source.URL}
                                </a>
                              ) : (
                                <span className="text-stone-700">{source.Title}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[#78716C] italic">{t.noPriceOptions}</p>
              )}
              <div className="border-t border-[#E2D9C8] pt-3">
                <label className="text-xs font-bold text-[#78716C]">{t.addAnotherMrp}</label>
                <div className="flex gap-2 mt-1">
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={manualMrp}
                    onChange={(event) => setManualMrp(event.target.value)}
                    placeholder={t.mrpPlace}
                    className="flex-1 min-w-0 bg-[#FFFDF9] text-stone-900 p-2 rounded-lg border border-[#D8CEBA] text-sm font-semibold focus:outline-none focus:border-[#991B1B]"
                  />
                  <button
                    type="button"
                    onClick={addManualMrp}
                    disabled={!(Number(manualMrp) > 0)}
                    className="px-3 rounded-lg bg-[#991B1B] hover:bg-[#B91C1C] text-white font-bold text-xs disabled:opacity-40 transition-all shadow-xs"
                  >
                    {t.addMrp}
                  </button>
                </div>
              </div>
              {pendingDraft.PriceOptions?.length === 0 &&
                pendingDraft.SearchResults?.length > 0 && (
                  <div className="border-t border-[#E2D9C8] pt-3">
                    <p className="text-xs text-[#78716C] font-bold uppercase mb-2">
                      {t.sourceLabel}
                    </p>
                    <ul className="space-y-1.5">
                      {pendingDraft.SearchResults.map((source, index) => (
                        <li key={`${source.URL}-${index}`} className="text-xs">
                          {source.URL ? (
                            <a
                              href={source.URL}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[#991B1B] hover:underline font-semibold"
                            >
                              {source.Title || source.URL}
                            </a>
                          ) : (
                            <span className="text-stone-700">{source.Title}</span>
                          )}
                          {source.Snippet && <p className="text-[#78716C] text-[11px] mt-0.5">{source.Snippet}</p>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              {confirmationError && (
                <p role="alert" className="text-xs text-red-600 font-semibold bg-red-50 p-2.5 rounded-lg border border-red-200">
                  {confirmationError}
                </p>
              )}
            </div>

            <div className="mt-6 flex space-x-3 gap-1">
              <button
                type="button"
                onClick={onCancel}
                className="w-1/3 py-3 px-4 rounded-xl bg-[#FFFDF9] hover:bg-[#F4EFE6] text-stone-800 font-bold border border-[#D8CEBA] transition-all text-xs shadow-2xs cursor-pointer"
              >
                {t.cancelBtn}
              </button>
              <button
                type="button"
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
                className="w-2/3 py-3 px-4 rounded-xl bg-[#991B1B] hover:bg-[#B91C1C] disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-xs shadow-xs transition-all cursor-pointer"
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
