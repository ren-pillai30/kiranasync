import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../../services/api";

export default function BarcodeScannerModal({
  isOpen,
  onClose,
  inventory = [],
  onAddToBill,
  onQuickSell,
  onRefreshAll,
}) {
  const [barcodeInput, setBarcodeInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [matchedItem, setMatchedItem] = useState(null);
  const [notFoundMessage, setNotFoundMessage] = useState("");
  const [selectedLinkItemId, setSelectedLinkItemId] = useState("");
  const [linkSuccessMessage, setLinkSuccessMessage] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setBarcodeInput("");
      setMatchedItem(null);
      setNotFoundMessage("");
      setSelectedLinkItemId("");
      setLinkSuccessMessage("");
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  const handleLookup = async (codeToLookup) => {
    const code = (codeToLookup || barcodeInput).trim();
    if (!code) return;

    setLoading(true);
    setMatchedItem(null);
    setNotFoundMessage("");
    setLinkSuccessMessage("");

    try {
      const res = await api.lookupBarcode(code);
      if (res.status === "success" && res.found && res.item) {
        setMatchedItem(res.item);
      } else {
        setNotFoundMessage(res.message || `No product found matching barcode ${code}.`);
      }
    } catch (err) {
      setNotFoundMessage(err.message || "Barcode lookup failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleLookup();
    }
  };

  const handleLinkBarcode = async () => {
    if (!selectedLinkItemId || !barcodeInput.trim()) return;
    setLoading(true);
    try {
      const res = await api.linkBarcode(selectedLinkItemId, barcodeInput.trim());
      if (res.status === "success") {
        setLinkSuccessMessage(`Barcode ${barcodeInput.trim()} linked successfully!`);
        if (onRefreshAll) onRefreshAll();
        // Re-lookup to show the newly linked product
        handleLookup(barcodeInput.trim());
      }
    } catch (err) {
      setNotFoundMessage(err.message || "Failed to link barcode.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 pointer-events-auto">
        <motion.div
          className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-pointer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        />

        <motion.div
          className="relative w-full max-w-md bg-[#FAF7F2] rounded-2xl shadow-2xl border-2 border-[#991B1B] overflow-hidden z-10 font-mono text-stone-800"
          initial={{ scale: 0.93, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.93, opacity: 0, y: 20 }}
        >
          {/* Header */}
          <div className="px-5 py-4 bg-[#FFFDF9] border-b border-[#E2D9C8] flex justify-between items-center">
            <div>
              <h3 className="text-base font-black text-stone-900 uppercase tracking-wider flex items-center gap-2">
                <span>📷</span>
                <span>Barcode Scanner / POS Counter</span>
              </h3>
              <p className="text-xs text-stone-500 mt-0.5">
                Scan with USB/Bluetooth scanner or enter digits manually
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-stone-400 hover:text-stone-900 text-2xl font-bold w-8 h-8 flex items-center justify-center rounded-lg hover:bg-stone-200 transition-all cursor-pointer"
            >
              &times;
            </button>
          </div>

          <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto custom-scrollbar">
            {/* Barcode Input Bar */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-stone-700 uppercase tracking-wide flex items-center justify-between">
                <span>Barcode Digits (EAN/UPC):</span>
                <span className="text-[10px] text-stone-400">Press Enter after scan</span>
              </label>
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="e.g. 8901030383748"
                  value={barcodeInput}
                  onChange={(e) => setBarcodeInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="flex-1 bg-white border border-[#D8CEBA] rounded-xl px-3.5 py-2 font-mono text-sm font-bold text-stone-900 focus:outline-none focus:ring-2 focus:ring-[#991B1B]"
                />
                <button
                  onClick={() => handleLookup()}
                  disabled={loading || !barcodeInput.trim()}
                  className="px-4 py-2 bg-[#991B1B] hover:bg-[#B91C1C] disabled:opacity-40 text-white font-bold text-xs rounded-xl shadow-xs transition-all cursor-pointer"
                >
                  {loading ? "Searching..." : "Lookup"}
                </button>
              </div>
            </div>

            {/* Matched Product Card */}
            {matchedItem && (
              <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-300 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
                      ✓ Product Found
                    </span>
                    <h4 className="text-sm font-black text-stone-900 mt-0.5">
                      {matchedItem.ItemName}
                    </h4>
                  </div>
                  <span className="text-base font-black text-emerald-900 tabular-nums">
                    ₹{Number(matchedItem.Price).toFixed(2)}
                  </span>
                </div>

                <div className="flex justify-between text-xs text-stone-600 border-t border-emerald-200/60 pt-2">
                  <span>Current Stock:</span>
                  <span className="font-bold text-stone-900 font-mono">
                    {matchedItem.StockQuantity} in stock
                  </span>
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => {
                      if (onAddToBill) {
                        onAddToBill({
                          billItems: [
                            {
                              item_name: matchedItem.ItemName,
                              quantity: 1,
                              unit_price: Number(matchedItem.Price),
                              item_total: Number(matchedItem.Price),
                            },
                          ],
                          customerName: "Walk-in Customer",
                          paymentMode: "cash",
                        });
                        onClose();
                      }
                    }}
                    className="flex-1 py-2 px-3 bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-xs rounded-lg shadow-2xs transition-all flex items-center justify-center gap-1 cursor-pointer"
                  >
                    <span>🧾</span>
                    <span>Add to Bill</span>
                  </button>

                  {onQuickSell && (
                    <button
                      onClick={() => {
                        onQuickSell(matchedItem);
                        onClose();
                      }}
                      className="flex-1 py-2 px-3 bg-stone-900 hover:bg-stone-800 text-white font-bold text-xs rounded-lg shadow-2xs transition-all flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <span>⚡</span>
                      <span>Quick Sale (1x)</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Not Found & Link Existing Product Box */}
            {notFoundMessage && !matchedItem && (
              <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-300 space-y-3">
                <div className="flex items-start gap-2">
                  <span className="text-amber-700 text-sm">⚠️</span>
                  <div>
                    <span className="text-xs font-bold text-amber-900 block">
                      Barcode Not In Catalog
                    </span>
                    <p className="text-[11px] text-amber-800/90 mt-0.5">
                      {notFoundMessage}
                    </p>
                  </div>
                </div>

                <div className="border-t border-amber-200/80 pt-2 space-y-2">
                  <span className="text-[11px] font-bold text-stone-800 block">
                    Link this barcode to an active inventory item:
                  </span>
                  <div className="flex gap-2">
                    <select
                      value={selectedLinkItemId}
                      onChange={(e) => setSelectedLinkItemId(e.target.value)}
                      className="flex-1 bg-white border border-stone-300 rounded-lg px-2.5 py-1.5 text-xs text-stone-900 focus:outline-none"
                    >
                      <option value="">Select product to link...</option>
                      {inventory.map((inv) => (
                        <option key={inv.ItemID} value={inv.ItemID}>
                          {inv.ItemName} (₹{inv.Price})
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleLinkBarcode}
                      disabled={loading || !selectedLinkItemId}
                      className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 disabled:opacity-40 text-white font-bold text-xs rounded-lg shadow-2xs transition-all cursor-pointer"
                    >
                      Link
                    </button>
                  </div>
                </div>
              </div>
            )}

            {linkSuccessMessage && (
              <div className="p-2.5 rounded-lg bg-emerald-100 text-emerald-900 text-xs font-bold text-center">
                ✓ {linkSuccessMessage}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-5 py-3 bg-[#FFFDF9] border-t border-[#E2D9C8] flex justify-end">
            <button
              onClick={onClose}
              className="py-2 px-4 rounded-xl border border-[#D8CEBA] text-stone-700 hover:bg-stone-100 font-bold text-xs transition-all cursor-pointer"
            >
              ✕ Close
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
