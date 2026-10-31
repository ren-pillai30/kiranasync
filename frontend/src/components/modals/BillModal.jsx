import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ── Amount in Words (Indian English, up to 99,999) ──────────────────────────
const ones = [
  "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
  "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
  "Seventeen", "Eighteen", "Nineteen",
];
const tens = [
  "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety",
];

function numberToWords(num) {
  if (num === 0) return "Zero";
  if (num < 0) return "Minus " + numberToWords(Math.abs(num));

  const rupees = Math.floor(num);
  const paise = Math.round((num - rupees) * 100);

  let words = convertInteger(rupees);
  words += " Rupees";

  if (paise > 0) {
    words += " and " + convertInteger(paise) + " Paise";
  }
  words += " Only";
  return words;
}

function convertInteger(n) {
  if (n === 0) return "";
  if (n < 20) return ones[n];
  if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 !== 0 ? " " + ones[n % 10] : "");
  if (n < 1000) return ones[Math.floor(n / 100)] + " Hundred" + (n % 100 !== 0 ? " and " + convertInteger(n % 100) : "");
  if (n < 100000) return convertInteger(Math.floor(n / 1000)) + " Thousand" + (n % 1000 !== 0 ? " " + convertInteger(n % 1000) : "");
  return String(n);
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function generateInvoiceNo() {
  const now = Date.now();
  return "KS-" + String(now).slice(-8);
}

function formatDateTime() {
  const now = new Date();
  const date = now.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
  const time = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
  return { date, time };
}

function roundOff(amount) {
  return Math.round(amount) - amount;
}

// ── Dashed Separator ────────────────────────────────────────────────────────
function DashedLine({ className = "" }) {
  return (
    <div
      className={`border-t border-dashed border-[#D8CEBA] my-2 ${className}`}
    />
  );
}

// ── Component ───────────────────────────────────────────────────────────────
export default function BillModal({
  isOpen,
  onClose,
  billItems = [],
  customerName = "Walk-in Customer",
  paymentMode = "cash",
  storeName = "KiranaSync Store",
  customerBalance = 0,
}) {
  const [invoiceNo] = useState(generateInvoiceNo);
  const { date, time } = useMemo(() => formatDateTime(), []);

  // ── Calculations ────────────────────────────────────────────────────────
  const subtotal = useMemo(
    () => billItems.reduce((sum, item) => sum + (item.item_total ?? 0), 0),
    [billItems]
  );

  const gstRate = 0; // placeholder
  const gstAmount = subtotal * (gstRate / 100);
  const rawTotal = subtotal + gstAmount;
  const roundOffAmt = roundOff(rawTotal);
  const grandTotal = Math.round(rawTotal);
  const newBalance = customerBalance + grandTotal;

  // ── Payment mode label & colors ─────────────────────────────────────────
  const modeConfig = {
    cash: { label: "💵 CASH", bg: "bg-emerald-100", text: "text-emerald-900", border: "border-emerald-300" },
    udhaar: { label: "📒 UDHAAR (CREDIT)", bg: "bg-red-100", text: "text-red-900", border: "border-red-300" },
    upi: { label: "📱 UPI", bg: "bg-[#FEF3C7]", text: "text-[#92400E]", border: "border-[#FDE68A]" },
  };
  const mode = modeConfig[paymentMode] ?? modeConfig.cash;

  // ── Print handler ───────────────────────────────────────────────────────
  function handlePrint() {
    window.print();
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 pointer-events-auto"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm cursor-pointer pointer-events-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="relative w-full max-w-md max-h-[90vh] flex flex-col bg-[#FAF7F2] rounded-2xl shadow-2xl border-2 border-[#991B1B] overflow-hidden pointer-events-auto z-10"
            initial={{ scale: 0.92, opacity: 0, y: 25 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.92, opacity: 0, y: 25 }}
            transition={{ type: "spring", damping: 25, stiffness: 350 }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Top Close Button */}
            <button
              type="button"
              onClick={onClose}
              className="absolute top-3 right-3 text-stone-400 hover:text-stone-900 text-2xl font-bold z-20 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-stone-200/60 transition-all cursor-pointer"
              title="Close"
            >
              &times;
            </button>

            {/* Scrollable Bill Content */}
            <div className="bill-printable overflow-y-auto custom-scrollbar flex-1 p-5 font-mono text-sm text-stone-800 bg-[#FFFDF9] m-3 rounded-xl border border-[#E2D9C8] shadow-xs">
              {/* ─── Store Header ─────────────────────────────── */}
              <div className="text-center mb-1">
                <h2 className="text-lg font-black text-stone-900 tracking-wide uppercase">
                  {storeName}
                </h2>
                <p className="text-xs text-[#78716C] leading-snug mt-0.5">
                  123, Main Market Road, Near Bus Stand
                  <br />
                  Bangalore, Karnataka - 560001
                </p>
                <p className="text-xs text-[#78716C] mt-0.5">
                  Ph: +91 98765 43210
                </p>
                <p className="text-[10px] text-[#A8A29E] mt-0.5 tracking-wide">
                  GSTIN: 29AXXXX1234X1ZX &nbsp;|&nbsp; FSSAI: 10020XXXXXX
                </p>
              </div>

              <DashedLine className="border-[#D8CEBA]" />

              {/* ─── Cash Memo Title ──────────────────────────── */}
              <p className="text-center text-xs font-bold text-[#991B1B] tracking-widest uppercase">
                — Cash Memo / Bill —
              </p>

              <DashedLine />

              {/* ─── Bill Meta ────────────────────────────────── */}
              <div className="space-y-0.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Invoice No.</span>
                  <span className="text-stone-900 font-bold">{invoiceNo}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Date</span>
                  <span className="text-stone-800">{date}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Time</span>
                  <span className="text-stone-800">{time}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Customer</span>
                  <span className="text-stone-900 font-bold">{customerName}</span>
                </div>
              </div>

              <DashedLine />

              {/* ─── Items Table Header ───────────────────────── */}
              <div className="grid grid-cols-[1.5rem_1fr_3.5rem_2.5rem_4rem] gap-x-1 text-[11px] font-bold text-[#57534E] uppercase tracking-wider mb-1">
                <span>#</span>
                <span>Item</span>
                <span className="text-right">Rate</span>
                <span className="text-right">Qty</span>
                <span className="text-right">Amt ₹</span>
              </div>

              <div className="border-t border-[#E2D9C8] mb-1" />

              {/* ─── Item Rows ────────────────────────────────── */}
              {billItems.length === 0 ? (
                <p className="text-center text-[#78716C] text-xs py-2 italic">
                  No items
                </p>
              ) : (
                billItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="grid grid-cols-[1.5rem_1fr_3.5rem_2.5rem_4rem] gap-x-1 text-xs py-0.5 text-stone-800 leading-tight"
                  >
                    <span className="text-[#78716C]">{idx + 1}</span>
                    <span className="truncate font-semibold text-stone-900">{item.item_name}</span>
                    <span className="text-right tabular-nums">
                      {Number(item.unit_price).toFixed(2)}
                    </span>
                    <span className="text-right tabular-nums">
                      {item.quantity}
                    </span>
                    <span className="text-right tabular-nums font-bold text-stone-900">
                      {Number(item.item_total).toFixed(2)}
                    </span>
                  </div>
                ))
              )}

              <DashedLine />

              {/* ─── Totals ───────────────────────────────────── */}
              <div className="space-y-0.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-[#78716C]">Subtotal</span>
                  <span className="text-stone-800 tabular-nums">
                    ₹{subtotal.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#78716C]">GST ({gstRate}%)</span>
                  <span className="text-stone-800 tabular-nums">
                    ₹{gstAmount.toFixed(2)}
                  </span>
                </div>
                {roundOffAmt !== 0 && (
                  <div className="flex justify-between">
                    <span className="text-[#78716C]">Round Off</span>
                    <span className="text-stone-800 tabular-nums">
                      {roundOffAmt > 0 ? "+" : ""}
                      ₹{roundOffAmt.toFixed(2)}
                    </span>
                  </div>
                )}
                <div className="border-t border-[#D8CEBA] my-1" />
                <div className="flex justify-between text-sm font-black">
                  <span className="text-stone-900">GRAND TOTAL</span>
                  <span className="text-[#991B1B] tabular-nums">
                    ₹{grandTotal.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* ─── Amount in Words ──────────────────────────── */}
              <p className="text-[10px] text-[#78716C] mt-1 italic leading-snug">
                Amount in words:{" "}
                <span className="text-stone-900 font-semibold">{numberToWords(grandTotal)}</span>
              </p>

              <DashedLine />

              {/* ─── Payment Mode Badge ──────────────────────── */}
              <div className="flex justify-center my-1">
                <span
                  className={`inline-block px-3 py-1 text-xs font-bold rounded-md border ${mode.bg} ${mode.text} ${mode.border} tracking-wide`}
                >
                  {mode.label}
                </span>
              </div>

              {/* ─── Udhaar / Khata Section ──────────────────── */}
              {paymentMode === "udhaar" && (
                <>
                  <DashedLine />
                  <div className="border border-dashed border-red-300 rounded-lg p-3 bg-red-50">
                    <p className="text-center text-xs font-bold text-red-900 tracking-wide uppercase mb-2">
                      📒 Khata / Credit Ledger
                    </p>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-[#78716C]">Previous Balance</span>
                        <span className="text-stone-800 tabular-nums">
                          ₹{Number(customerBalance).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#78716C]">Current Bill (+)</span>
                        <span className="text-red-700 tabular-nums font-bold">
                          ₹{grandTotal.toFixed(2)}
                        </span>
                      </div>
                      <div className="border-t border-red-200 my-1" />
                      <div className="flex justify-between font-bold text-sm">
                        <span className="text-red-900">New Balance</span>
                        <span className="text-red-900 tabular-nums">
                          ₹{newBalance.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <DashedLine />

              {/* ─── Footer / Thank You ──────────────────────── */}
              <div className="text-center space-y-1 mt-1 mb-2">
                <p className="text-xs text-[#78716C] italic font-semibold">
                  "Thank you for shopping with us!"
                </p>
                <p className="text-[10px] text-[#A8A29E]">
                  Goods once sold will not be taken back.
                  <br />
                  Subject to Bangalore jurisdiction only.
                </p>
                <p className="text-[10px] text-[#991B1B] font-bold mt-2 tracking-widest">
                  ★ ★ ★ Powered by KiranaSync ★ ★ ★
                </p>
              </div>
            </div>

            {/* ─── Action Buttons (outside scrollable area) ──── */}
            <div className="flex border-t border-[#E2D9C8] shrink-0 bg-[#FAF7F2] p-3.5 gap-3 pointer-events-auto">
              <button
                type="button"
                onClick={handlePrint}
                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-xs font-bold text-white bg-[#991B1B] hover:bg-[#B91C1C] transition-all cursor-pointer shadow-xs"
              >
                🖨️ Print Bill
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-xs font-bold text-stone-800 bg-[#FFFDF9] hover:bg-[#F4EFE6] border border-[#D8CEBA] transition-all cursor-pointer shadow-2xs"
              >
                ✕ Close
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
