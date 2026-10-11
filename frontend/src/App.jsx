import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import RecordRTC, { StereoAudioRecorder } from 'recordrtc'

// Localization Dictionary
const text = {
  en: {
    title: "KiranaSync Live Dashboard",
    toggleLang: "हिंदी (Hindi)",
    invTitle: "📦 Live Inventory",
    addBtn: "+ Add",
    editBtn: "Edit",
    saveBtn: "Save",
    itemPlace: "Brand / Item Name",
    qtyPlace: "Stock Qty",
    pricePlace: "Price (₹)",
    saveItem: "Save Item",
    thItem: "Item Name",
    thStock: "Stock",
    thPrice: "Price",
    thAction: "Action",
    credTitle: "📒 Customer Udhaar",
    custPlace: "Customer Name",
    balPlace: "Balance Due (₹)",
    saveCust: "Save Customer",
    thCust: "Customer",
    thBal: "Balance Due",
    voiceTitle: "KiranaSync Voice",
    defaultListening: "Listening for voice command...",
    processing: "Processing with Gnani AI...",
    micError: "Please allow microphone permissions.",
    connError: "Failed to connect to backend."
  },
  hi: {
    title: "किरानासिंक लाइव डैशबोर्ड",
    toggleLang: "English",
    invTitle: "📦 लाइव इन्वेंटरी",
    addBtn: "+ जोड़ें",
    editBtn: "संपादित करें",
    saveBtn: "सहेजें",
    itemPlace: "आइटम का नाम",
    qtyPlace: "स्टॉक मात्रा",
    pricePlace: "कीमत (₹)",
    saveItem: "आइटम सहेजें",
    thItem: "आइटम",
    thStock: "स्टॉक",
    thPrice: "कीमत",
    thAction: "कार्रवाई",
    credTitle: "📒 ग्राहक उधार",
    custPlace: "ग्राहक का नाम",
    balPlace: "बकाया राशि (₹)",
    saveCust: "ग्राहक सहेजें",
    thCust: "ग्राहक",
    thBal: "बकाया राशि",
    voiceTitle: "किरानासिंक वॉयस",
    defaultListening: "वॉयस कमांड सुन रहा है...",
    processing: "ज्ञानी एआई के साथ प्रोसेस कर रहा है...",
    micError: "कृपया माइक्रोफ़ोन अनुमति दें।",
    connError: "बैकएंड से कनेक्ट करने में विफल।"
  }
};

export default function App() {
  const [lang, setLang] = useState('en');
  const t = text[lang];

  const [isActive, setIsActive] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [transcript, setTranscript] = useState(t.defaultListening);
  const [dbAction, setDbAction] = useState(null);
  
  const [inventory, setInventory] = useState([]);
  const [credit, setCredit] = useState([]);
  
  const [showAddInv, setShowAddInv] = useState(false);
  const [invForm, setInvForm] = useState({ ItemName: '', StockQuantity: '', Price: '' });
  
  const [showAddCust, setShowAddCust] = useState(false);
  const [custForm, setCustForm] = useState({ CustomerName: '', Amount: '' });

  // Inline Editing States
  const [editInvId, setEditInvId] = useState(null);
  const [editInvName, setEditInvName] = useState('');
  
  const [editCustId, setEditCustId] = useState(null);
  const [editCustName, setEditCustName] = useState('');

  const recordRTC = useRef(null);

  useEffect(() => {
    setTranscript(t.defaultListening);
  }, [lang, t.defaultListening]);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/dashboard');
      const data = await response.json();
      if (data.status === 'success') {
        setInventory(data.inventory);
        setCredit(data.credit);
      }
    } catch (error) {
      console.error("Dashboard fetch error:", error);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleAddInventory = async (e) => {
    e.preventDefault();
    await fetch('http://127.0.0.1:5000/api/inventory/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(invForm)
    });
    setInvForm({ ItemName: '', StockQuantity: '', Price: '' });
    setShowAddInv(false);
    fetchDashboardData();
  };

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    await fetch('http://127.0.0.1:5000/api/credit/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(custForm)
    });
    setCustForm({ CustomerName: '', Amount: '' });
    setShowAddCust(false);
    fetchDashboardData();
  };

  const handleEditInventory = async (id) => {
    await fetch('http://127.0.0.1:5000/api/inventory/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ItemID: id, NewItemName: editInvName })
    });
    setEditInvId(null);
    fetchDashboardData();
  };

  const handleEditCustomer = async (id) => {
    await fetch('http://127.0.0.1:5000/api/credit/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ CustomerID: id, NewCustomerName: editCustName })
    });
    setEditCustId(null);
    fetchDashboardData();
  };

  const startRecording = async () => {
    try {
      setIsActive(true);
      setShowDashboard(false);
      setTranscript(t.defaultListening);
      setDbAction(null);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      recordRTC.current = new RecordRTC(stream, { 
        type: 'audio', 
        mimeType: 'audio/wav',
        recorderType: StereoAudioRecorder,
        desiredSampRate: 16000,
        numberOfAudioChannels: 1
      });
      
      recordRTC.current.startRecording();

      setTimeout(() => {
        if (recordRTC.current) {
          recordRTC.current.stopRecording(async () => {
            setTranscript(t.processing);
            const audioBlob = recordRTC.current.getBlob();
            stream.getTracks().forEach(track => track.stop());

            const formData = new FormData();
            formData.append('audio', audioBlob, 'command.wav');

            try {
              const response = await fetch('http://127.0.0.1:5000/api/process-audio', { method: 'POST', body: formData });
              const data = await response.json();
              if (data.status === 'success') {
                setTranscript(data.transcript);
                setDbAction(data.database_action);
              } else {
                setTranscript("Error: " + (data.error || "Failed to parse"));
              }
            } catch (error) {
              setTranscript(t.connError);
            }

            setTimeout(() => {
              setIsActive(false);
              setShowDashboard(true);
            }, 4000);
          });
        }
      }, 4000);
    } catch (err) {
      setTranscript(t.micError);
    }
  };

  return (
    <div className="flex items-center justify-center w-screen h-screen p-6 pointer-events-none">
      <button id="voice-trigger" onClick={startRecording} className="hidden">Voice</button>
      <button id="dashboard-trigger" onClick={() => setShowDashboard(!showDashboard)} className="hidden">Dash</button>

      <AnimatePresence>
        {isActive && (
          <motion.div 
            initial={{ opacity: 0, y: 50, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="absolute bottom-6 right-6 w-96 bg-gray-900/95 backdrop-blur-md border border-gray-700/80 rounded-2xl p-5 shadow-2xl pointer-events-auto"
          >
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">{t.voiceTitle}</span>
            </div>
            <p className="text-base font-semibold text-white mb-4 leading-snug">"{transcript}"</p>
            {dbAction && (
              <motion.div className={`p-3 rounded-xl flex items-center space-x-3 border ${dbAction.status === 'success' ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300' : 'bg-rose-500/10 border-rose-500/40 text-rose-300'}`}>
                <span className="text-sm font-medium">{dbAction.message}</span>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showDashboard && !isActive && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-5xl bg-gray-900/95 backdrop-blur-xl border border-gray-700 rounded-2xl p-8 shadow-2xl pointer-events-auto max-h-[90vh] overflow-y-auto"
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-white">{t.title}</h2>
              <button 
                onClick={() => setLang(lang === 'en' ? 'hi' : 'en')}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium border border-gray-600 transition-colors"
              >
                {t.toggleLang}
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-8">
              {/* INVENTORY PANEL */}
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-blue-400">{t.invTitle}</h3>
                  <button onClick={() => setShowAddInv(!showAddInv)} className="text-sm bg-blue-500/20 text-blue-400 px-3 py-1 rounded hover:bg-blue-500/40">{t.addBtn}</button>
                </div>
                
                {showAddInv && (
                  <form onSubmit={handleAddInventory} className="bg-gray-800 p-4 rounded-xl mb-4 border border-gray-700 flex flex-col space-y-2">
                    <input required type="text" placeholder={t.itemPlace} className="bg-gray-700 text-white p-2 rounded" value={invForm.ItemName} onChange={e => setInvForm({...invForm, ItemName: e.target.value})} />
                    <div className="flex space-x-2">
                      <input required type="number" placeholder={t.qtyPlace} className="bg-gray-700 text-white p-2 rounded w-1/2" value={invForm.StockQuantity} onChange={e => setInvForm({...invForm, StockQuantity: e.target.value})} />
                      <input required type="number" placeholder={t.pricePlace} className="bg-gray-700 text-white p-2 rounded w-1/2" value={invForm.Price} onChange={e => setInvForm({...invForm, Price: e.target.value})} />
                    </div>
                    <button type="submit" className="bg-blue-500 text-white py-2 rounded font-semibold mt-2">{t.saveItem}</button>
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
                          <td className="px-4 py-3"><span className={`px-2 py-1 rounded-md ${item.StockQuantity < 10 ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}`}>{item.StockQuantity}</span></td>
                          <td className="px-4 py-3">₹{item.Price}</td>
                          <td className="px-4 py-3 text-right">
                            {editInvId === item.ItemID ? (
                              <button onClick={() => handleEditInventory(item.ItemID)} className="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1 bg-emerald-500/20 rounded ml-2">{t.saveBtn}</button>
                            ) : (
                              <button onClick={() => { setEditInvId(item.ItemID); setEditInvName(item.ItemName); }} className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-700 rounded ml-2">{t.editBtn}</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* CREDIT PANEL */}
              <div>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-rose-400">{t.credTitle}</h3>
                  <button onClick={() => setShowAddCust(!showAddCust)} className="text-sm bg-rose-500/20 text-rose-400 px-3 py-1 rounded hover:bg-rose-500/40">{t.addBtn}</button>
                </div>

                {showAddCust && (
                  <form onSubmit={handleAddCustomer} className="bg-gray-800 p-4 rounded-xl mb-4 border border-gray-700 flex flex-col space-y-2">
                    <input required type="text" placeholder={t.custPlace} className="bg-gray-700 text-white p-2 rounded" value={custForm.CustomerName} onChange={e => setCustForm({...custForm, CustomerName: e.target.value})} />
                    <input required type="number" placeholder={t.balPlace} className="bg-gray-700 text-white p-2 rounded" value={custForm.Amount} onChange={e => setCustForm({...custForm, Amount: e.target.value})} />
                    <button type="submit" className="bg-rose-500 text-white py-2 rounded font-semibold mt-2">{t.saveCust}</button>
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
                          <td className="px-4 py-3 text-rose-400 font-semibold">₹{person.OutstandingBalance}</td>
                          <td className="px-4 py-3 text-right">
                            {editCustId === person.CustomerID ? (
                              <button onClick={() => handleEditCustomer(person.CustomerID)} className="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1 bg-emerald-500/20 rounded ml-2">{t.saveBtn}</button>
                            ) : (
                              <button onClick={() => { setEditCustId(person.CustomerID); setEditCustName(person.CustomerName); }} className="text-gray-400 hover:text-white text-xs px-2 py-1 bg-gray-700 rounded ml-2">{t.editBtn}</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}