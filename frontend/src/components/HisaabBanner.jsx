export default function HisaabBanner({ hisaabData }) {
  if (!hisaabData) return null;

  return (
    <div className="bg-gradient-to-r from-gray-800 to-gray-800/60 border border-gray-700 p-4 rounded-xl mb-6 flex justify-between items-center text-xs">
      <div>
        <span className="text-gray-400 uppercase tracking-wider block font-semibold">Today's Revenue</span>
        <span className="text-lg font-bold text-emerald-400">₹{hisaabData.TotalRevenue}</span>
      </div>
      <div>
        <span className="text-gray-400 uppercase tracking-wider block font-semibold">Cash Collected</span>
        <span className="text-lg font-bold text-blue-400">₹{hisaabData.CashCollected}</span>
      </div>
      <div>
        <span className="text-gray-400 uppercase tracking-wider block font-semibold">Repayments</span>
        <span className="text-lg font-bold text-amber-400">₹{hisaabData.RepaymentsTotal}</span>
      </div>
      <div>
        <span className="text-gray-400 uppercase tracking-wider block font-semibold">Total Customer Udhaar</span>
        <span className="text-lg font-bold text-rose-400">₹{hisaabData.TotalOutstandingDebt}</span>
      </div>
    </div>
  );
}

