export default function HisaabBanner({ hisaabData }) {
  if (!hisaabData) return null;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
      {/* TODAY'S SALES */}
      <div className="bg-[#FFFDF9] border border-[#E2D9C8] p-4 rounded-xl shadow-xs hover:shadow-md transition-all flex flex-col justify-between border-t-4 border-t-[#991B1B]">
        <div className="flex items-center justify-between text-[#78716C] text-xs mb-2">
          <span className="uppercase font-bold tracking-wider text-[10px]">Today's Sales</span>
          <span className="text-base p-1 rounded-md bg-[#FEF3C7]"></span>
        </div>
        <div className="text-2xl font-black font-mono text-[#991B1B]">
          ₹{Math.abs(Number(hisaabData.TotalRevenue) || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-[#78716C] mt-1 font-medium">Gross counter volume</span>
      </div>

      {/* CASH COLLECTED */}
      <div className="bg-[#FFFDF9] border border-[#E2D9C8] p-4 rounded-xl shadow-xs hover:shadow-md transition-all flex flex-col justify-between border-t-4 border-t-emerald-700">
        <div className="flex items-center justify-between text-[#78716C] text-xs mb-2">
          <span className="uppercase font-bold tracking-wider text-[10px]">Cash in Register</span>
          <span className="text-base p-1 rounded-md bg-emerald-50"></span>
        </div>
        <div className="text-2xl font-black font-mono text-emerald-800">
          ₹{Math.abs(Number(hisaabData.CashCollected) || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-[#78716C] mt-1 font-medium">Opening cash + today&apos;s collections</span>
      </div>

      {/* REPAYMENTS */}
      <div className="bg-[#FFFDF9] border border-[#E2D9C8] p-4 rounded-xl shadow-xs hover:shadow-md transition-all flex flex-col justify-between border-t-4 border-t-amber-600">
        <div className="flex items-center justify-between text-[#78716C] text-xs mb-2">
          <span className="uppercase font-bold tracking-wider text-[10px]">Udhaar Recovered</span>
          <span className="text-base p-1 rounded-md bg-amber-50"></span>
        </div>
        <div className="text-2xl font-black font-mono text-[#B45309]">
          ₹{Math.abs(Number(hisaabData.RepaymentsTotal) || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-[#78716C] mt-1 font-medium">Credit repayments received</span>
      </div>

      {/* TOTAL OUTSTANDING DEBT */}
      <div className="bg-[#FFFDF9] border border-[#E2D9C8] p-4 rounded-xl shadow-xs hover:shadow-md transition-all flex flex-col justify-between border-t-4 border-t-red-600">
        <div className="flex items-center justify-between text-[#78716C] text-xs mb-2">
          <span className="uppercase font-bold tracking-wider text-[10px]">Total Customer Udhaar</span>
          <span className="text-base p-1 rounded-md bg-red-50"></span>
        </div>
        <div className="text-2xl font-black font-mono text-red-700">
          ₹{Math.abs(Number(hisaabData.TotalOutstandingDebt) || 0).toLocaleString('en-IN')}
        </div>
        <span className="text-[11px] text-[#78716C] mt-1 font-medium">Total pending debt across khata</span>
      </div>
    </div>
  );
}
