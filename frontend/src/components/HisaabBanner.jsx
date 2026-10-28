export default function HisaabBanner({ hisaabData }) {
  if (!hisaabData) return null;

  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {/* TODAY'S SALES */}
      <div className="bg-gray-800/90 border border-gray-700/80 p-4 rounded-xl shadow-sm flex flex-col justify-between">
        <div className="flex items-center justify-between text-gray-400 text-xs mb-2">
          <span className="uppercase font-semibold tracking-wider">Today's Sales</span>
          <span className="text-base">📈</span>
        </div>
        <div className="text-2xl font-bold font-mono text-emerald-400">
          ₹{Number(hisaabData.TotalRevenue || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-gray-400 mt-1">Gross counter volume</span>
      </div>

      {/* CASH COLLECTED */}
      <div className="bg-gray-800/90 border border-gray-700/80 p-4 rounded-xl shadow-sm flex flex-col justify-between">
        <div className="flex items-center justify-between text-gray-400 text-xs mb-2">
          <span className="uppercase font-semibold tracking-wider">Cash in Register</span>
          <span className="text-base">💵</span>
        </div>
        <div className="text-2xl font-bold font-mono text-blue-400">
          ₹{Number(hisaabData.CashCollected || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-gray-400 mt-1">Physical cash drawer</span>
      </div>

      {/* REPAYMENTS */}
      <div className="bg-gray-800/90 border border-gray-700/80 p-4 rounded-xl shadow-sm flex flex-col justify-between">
        <div className="flex items-center justify-between text-gray-400 text-xs mb-2">
          <span className="uppercase font-semibold tracking-wider">Udhaar Recovered</span>
          <span className="text-base">🔄</span>
        </div>
        <div className="text-2xl font-bold font-mono text-amber-400">
          ₹{Number(hisaabData.RepaymentsTotal || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-gray-400 mt-1">Credit repayments received</span>
      </div>

      {/* TOTAL OUTSTANDING DEBT */}
      <div className="bg-gray-800/90 border border-gray-700/80 p-4 rounded-xl shadow-sm flex flex-col justify-between">
        <div className="flex items-center justify-between text-gray-400 text-xs mb-2">
          <span className="uppercase font-semibold tracking-wider">Total Customer Udhaar</span>
          <span className="text-base">📒</span>
        </div>
        <div className="text-2xl font-bold font-mono text-rose-400">
          ₹{Number(hisaabData.TotalOutstandingDebt || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-gray-400 mt-1">Total pending debt across khata</span>
      </div>
    </div>
  );
}
