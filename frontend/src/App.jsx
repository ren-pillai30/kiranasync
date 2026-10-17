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
    ledgerTitle: "📜 Transaction Ledger",
    ledgerEmpty: "No transactions yet.",
    ledgerDate: "Date & Time",
    ledgerType: "Type",
    ledgerEntity: "Item / Customer",
    ledgerQuantity: "Quantity",
    ledgerAmount: "Amount",
    ledgerDetails: "Details",
    custPlace: "Customer Name",
    balPlace: "Balance Due (₹)",
    saveCust: "Save Customer",
    thCust: "Customer",
    thBal: "Balance Due",
    voiceTitle: "KiranaSync Voice",
    defaultListening: "Listening for voice command...",
    processing: "Processing with Gnani AI...",
    micError: "Please allow microphone permissions.",
    connError: "Failed to connect to backend.",
    confirmTitle: "Confirm New Product Details",
    confirmDesc: "Review the product name, stock quantity, and MRP. Online prices are suggestions; verify them before adding.",
    mrpPlace: "MRP per item (₹)",
    mrpOptions: "Select one or more MRP options",
    chooseMrp: "Choose MRP",
    addAnotherMrp: "Add another MRP",
    addMrp: "Add MRP",
    mrpSources: "Sources",
    manualMrp: "Manual MRP",
    quantityForMrp: "Stock for this MRP",
    noPriceOptions: "No online prices found. Add an MRP manually below.",
    productVariantNote: "Each selected MRP will be added as a separate inventory item with its MRP in the name.",
    searchFound: "Suggested MRP found online. Verify it against the source before adding.",
    searchPriceOnly: "An online price was found, but it may not be the MRP. Verify the product packaging.",
    lookupUnavailable: "No online MRP found. Enter the correct MRP to continue.",
    searchError: "The web search could not be completed. Enter and verify the MRP manually.",
    searchAgain: "Search this product name",
    searching: "Searching...",
    editNameToSearch: "Change the name, then search again to refresh matching sources.",
    purchaseTotal: "Purchase total",
    sourceLabel: "Web sources",
    confirmAddBtn: "Confirm & Add to Inventory",
    cancelBtn: "Cancel",
    selectProductTitle: "Choose the exact product",
    selectProductDesc: "More than one version matches this command. Select the correct MRP/size before inventory is changed.",
    availableStock: "In stock",
    confirmProduct: "Confirm product",
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
    ledgerTitle: "📜 लेन-देन का बहीखाता",
    ledgerEmpty: "अभी तक कोई लेन-देन नहीं।",
    ledgerDate: "दिनांक और समय",
    ledgerType: "प्रकार",
    ledgerEntity: "आइटम / ग्राहक",
    ledgerQuantity: "मात्रा",
    ledgerAmount: "राशि",
    ledgerDetails: "विवरण",
    custPlace: "ग्राहक का नाम",
    balPlace: "बकाया राशि (₹)",
    saveCust: "ग्राहक सहेजें",
    thCust: "ग्राहक",
    thBal: "बकाया राशि",
    voiceTitle: "किरानासिंक वॉयस",
    defaultListening: "वॉयस कमांड सुन रहा है...",
    processing: "ज्ञानी एआई के साथ प्रोसेस कर रहा है...",
    micError: "कृपया माइक्रोफ़ोन अनुमति दें।",
    connError: "बैकएंड से कनेक्ट करने में विफल।",
    confirmTitle: "नए उत्पाद विवरण की पुष्टि करें",
    confirmDesc: "उत्पाद का नाम, स्टॉक मात्रा और MRP जांचें। ऑनलाइन कीमत केवल सुझाव है—जोड़ने से पहले सत्यापित करें।",
    mrpPlace: "प्रति आइटम MRP (₹)",
    mrpOptions: "एक या अधिक MRP विकल्प चुनें",
    chooseMrp: "MRP चुनें",
    addAnotherMrp: "एक और MRP जोड़ें",
    addMrp: "MRP जोड़ें",
    mrpSources: "स्रोत",
    manualMrp: "मैन्युअल MRP",
    quantityForMrp: "इस MRP का स्टॉक",
    noPriceOptions: "ऑनलाइन कीमतें नहीं मिलीं। नीचे MRP मैन्युअल रूप से जोड़ें।",
    productVariantNote: "चुना गया हर MRP नाम में MRP के साथ अलग इन्वेंटरी आइटम बनेगा।",
    searchFound: "ऑनलाइन सुझाया गया MRP मिला। जोड़ने से पहले स्रोत से जांचें।",
    searchPriceOnly: "ऑनलाइन कीमत मिली है, लेकिन यह MRP नहीं भी हो सकती। पैकेजिंग पर जांचें।",
    lookupUnavailable: "ऑनलाइन MRP नहीं मिला। आगे बढ़ने के लिए सही MRP दर्ज करें।",
    searchError: "वेब खोज पूरी नहीं हो सकी। MRP स्वयं दर्ज करके सत्यापित करें।",
    searchAgain: "इस उत्पाद के नाम से खोजें",
    searching: "खोज रहे हैं...",
    editNameToSearch: "नाम बदलें, फिर संबंधित स्रोतों के लिए दोबारा खोजें।",
    purchaseTotal: "कुल खरीद राशि",
    sourceLabel: "वेब स्रोत",
    confirmAddBtn: "पुष्टि करें और जोड़ें",
    cancelBtn: "रद्द करें",
    selectProductTitle: "सही उत्पाद चुनें",
    selectProductDesc: "इस कमांड से एक से अधिक उत्पाद मिलते हैं। स्टॉक बदलने से पहले सही MRP/आकार चुनें।",
    availableStock: "उपलब्ध स्टॉक",
    confirmProduct: "उत्पाद की पुष्टि करें"
  }
};

export default function App() {
  const [lang, setLang] = useState('en');
  const t = text[lang];

  const [isActive, setIsActive] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [transcript, setTranscript] = useState(t.defaultListening);
  const [dbAction, setDbAction] = useState(null);
  
  // Confirmation Modal State
  const [pendingDraft, setPendingDraft] = useState(null);
  const [pendingItemChoice, setPendingItemChoice] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [confirmationError, setConfirmationError] = useState('');
  const [isSearchingProduct, setIsSearchingProduct] = useState(false);
  const [manualMrp, setManualMrp] = useState('');

  const [inventory, setInventory] = useState([]);
  const [credit, setCredit] = useState([]);
  const [transactions, setTransactions] = useState([]);
  
  const [showAddInv, setShowAddInv] = useState(false);
  const [invForm, setInvForm] = useState({ ItemName: '', StockQuantity: '', Price: '' });
  
  const [showAddCust, setShowAddCust] = useState(false);
  const [custForm, setCustForm] = useState({ CustomerName: '', Amount: '' });

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

  const fetchLedgerData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/ledger');
      const data = await response.json();
      if (data.status === 'success') {
        setTransactions(data.transactions);
      }
    } catch (error) {
      console.error("Transaction ledger fetch error:", error);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchLedgerData();
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
    fetchLedgerData();
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
    fetchLedgerData();
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

  const submitConfirmation = async () => {
    setConfirmationError('');
    const selectedItems = (pendingDraft.PriceOptions || [])
      .filter(option => option.Selected)
      .map(option => ({ Price: option.Price, Quantity: option.Quantity }));
    if (!selectedItems.length) {
      setConfirmationError(t.chooseMrp);
      return;
    }
    try {
      const response = await fetch('http://127.0.0.1:5000/api/inventory/confirm-restock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ItemName: pendingDraft.ItemName,
          Items: selectedItems,
          RawCommand: pendingDraft.RawCommand,
        })
      });
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        setConfirmationError(result.error || t.connError);
        return;
      }
      setPendingDraft(null);
      setManualMrp('');
      fetchDashboardData();
      fetchLedgerData();
    } catch (error) {
      console.error("Product confirmation error:", error);
      setConfirmationError(t.connError);
    }
  };

  const submitItemChoice = async () => {
    if (!pendingItemChoice || selectedItemId === null) return;
    setConfirmationError('');
    try {
      const response = await fetch('http://127.0.0.1:5000/api/inventory/confirm-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ItemID: selectedItemId,
          Intent: pendingItemChoice.Intent,
          Quantity: pendingItemChoice.Quantity,
          RawCommand: pendingItemChoice.RawCommand,
        }),
      });
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        setConfirmationError(result.error || t.connError);
        return;
      }
      setPendingItemChoice(null);
      setSelectedItemId(null);
      setConfirmationError('');
      setDbAction(result.database_action);
      fetchDashboardData();
      fetchLedgerData();
    } catch (error) {
      console.error("Inventory variant confirmation error:", error);
      setConfirmationError(t.connError);
    }
  };

  const searchEditedProductName = async () => {
    if (!pendingDraft?.ItemName?.trim()) {
      return;
    }
    const requestedName = pendingDraft.ItemName.trim();
    setIsSearchingProduct(true);
    setConfirmationError('');
    setPendingDraft(current => current ? ({
      ...current,
      Price: null,
      PriceFound: false,
      PriceIsMRP: false,
      SearchStatus: 'searching',
      SearchMessage: '',
      SearchResults: [],
      PriceOptions: [],
    }) : current);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/product-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ItemName: requestedName }),
      });
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        setConfirmationError(result.error || t.connError);
        setPendingDraft(current => current ? ({
          ...current,
          SearchStatus: 'error',
          SearchResults: [],
        }) : current);
        return;
      }
      setPendingDraft(current => current && current.ItemName.trim() === requestedName
        ? {
            ...current,
            ...result,
            StockQuantity: current.StockQuantity,
            RawCommand: current.RawCommand,
            PriceOptions: (result.PriceOptions || []).map((option, index) => ({
              ...option,
              Quantity: current.StockQuantity,
              Selected: index === 0,
            })),
          }
        : current);
    } catch (error) {
      console.error("Product search error:", error);
      setConfirmationError(t.connError);
      setPendingDraft(current => current ? ({
        ...current,
        SearchStatus: 'error',
        SearchResults: [],
      }) : current);
    } finally {
      setIsSearchingProduct(false);
    }
  };

  const addManualMrp = () => {
    const price = Number(manualMrp);
    if (!(price > 0) || !Number.isFinite(price)) {
      return;
    }
    setPendingDraft(current => {
      if (!current) return current;
      const options = current.PriceOptions || [];
      if (options.some(option => Number(option.Price) === price)) {
        return {
          ...current,
          PriceOptions: options.map(option => (
            Number(option.Price) === price ? { ...option, Selected: true } : option
          )),
        };
      }
      return {
        ...current,
        PriceOptions: [
          ...options,
          {
            Price: price,
            PriceIsMRP: false,
            IsManual: true,
            Sources: [],
            Quantity: current.StockQuantity,
            Selected: true,
          },
        ],
      };
    });
    setManualMrp('');
  };

  const handleMinimize = () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.minimize();
    }
  };

  const handleClose = () => {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.close();
    }
  };

  const startRecording = async () => {
    try {
      setIsActive(true);
      setShowDashboard(false);
      setTranscript(t.defaultListening);
      setDbAction(null);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      recordRTC.current = new RecordRTC(stream, { 
        type: 'audio', mimeType: 'audio/wav', recorderType: StereoAudioRecorder, desiredSampRate: 16000, numberOfAudioChannels: 1
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
                if (data.database_action?.status === 'success') {
                  fetchDashboardData();
                  fetchLedgerData();
                }
                
                // Route to Confirmation Modal if needed
                if (data.database_action && data.database_action.status === 'pending_confirmation') {
                  const draft = data.database_action.draft;
                  const options = draft.PriceOptions || (
                    Number(draft.Price) > 0
                      ? [{ Price: Number(draft.Price), PriceIsMRP: draft.PriceIsMRP, Sources: [] }]
                      : []
                  );
                  setPendingDraft({
                    ...draft,
                    PriceOptions: options.map((option, index) => ({
                      ...option,
                      Quantity: draft.StockQuantity,
                      Selected: index === 0,
                    })),
                  });
                  setManualMrp('');
                  setConfirmationError('');
                  setDbAction({ status: 'pending', message: data.database_action.message });
                  setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 2000);
                } else if (data.database_action?.status === 'pending_selection') {
                  setPendingItemChoice(data.database_action.draft);
                  setSelectedItemId(null);
                  setConfirmationError('');
                  setDbAction({ status: 'pending', message: data.database_action.message });
                  setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 1000);
                } else {
                  setDbAction(data.database_action);
                  setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 4000);
                }
              } else {
                setTranscript("Error: " + (data.error || "Failed to parse"));
                setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 4000);
              }
            } catch (error) {
              setTranscript(t.connError);
              setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 4000);
            }
          });
        }
      }, 4000);
    } catch (err) {
      setTranscript(t.micError);
    }
  };

  return (
    <div className="flex flex-col w-screen h-screen relative bg-transparent overflow-hidden">
      
      {/* WINDOW CONTROLS HEADER */}
      <header className="overlay-header absolute top-0 left-0 w-full flex justify-between items-center px-4 py-2 bg-gray-900/90 backdrop-blur-md border-b border-gray-700 pointer-events-auto z-50">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-gray-400 tracking-wider">KIRANASYNC</span>
        </div>
        <div className="window-controls flex space-x-1">
          <button className="control-btn minimize" onClick={handleMinimize} title="Minimize">&minus;</button>
          <button className="control-btn close" onClick={handleClose} title="Close">&times;</button>
        </div>
      </header>

      {/* MAIN CONTENT AREA */}
      <div className="flex-grow flex items-center justify-center p-6 pointer-events-none mt-10">
        <button id="voice-trigger" onClick={startRecording} className="hidden">Voice</button>
        <button id="dashboard-trigger" onClick={() => setShowDashboard(!showDashboard)} className="hidden">Dash</button>

        {/* CONFIRMATION OVERLAY MODAL */}
        <AnimatePresence>
          {pendingDraft && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto"
            >
              <motion.div 
                initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }}
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
                    <input type="text" className="w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600 focus:border-blue-500 outline-none"
                      value={pendingDraft.ItemName} onChange={e => {
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
                      }} />
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
                        <div key={`${option.Price}-${index}`} className={`block p-3 rounded-xl border ${option.Selected ? 'border-blue-500 bg-blue-500/10' : 'border-gray-700 bg-gray-700/40'}`}>
                          <div className="flex items-start gap-3">
                            <input
                              type="checkbox"
                              checked={Boolean(option.Selected)}
                              aria-label={`${t.chooseMrp} ₹${option.Price}`}
                              onChange={event => setPendingDraft(current => ({
                                ...current,
                                PriceOptions: current.PriceOptions.map((entry, entryIndex) => (
                                  entryIndex === index ? { ...entry, Selected: event.target.checked } : entry
                                )),
                              }))}
                              className="mt-1 accent-blue-500"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex justify-between items-center">
                                <span className="font-semibold text-white">
                                  ₹{Number(option.Price).toLocaleString('en-IN')}
                                  {option.IsManual ? ` · ${t.manualMrp}` : option.PriceIsMRP ? ' · MRP' : ' · online price'}
                                </span>
                                <span className="text-xs text-gray-400">
                                  {t.purchaseTotal}: ₹{(Number(option.Price) * Number(option.Quantity)).toLocaleString('en-IN')}
                                </span>
                              </div>
                              <div className="mt-2">
                                <label className="text-xs text-gray-400">{t.quantityForMrp}</label>
                                <input
                                  type="number"
                                  min="1"
                                  step="1"
                                  value={option.Quantity}
                                  onChange={event => setPendingDraft(current => ({
                                    ...current,
                                    PriceOptions: current.PriceOptions.map((entry, entryIndex) => (
                                      entryIndex === index ? { ...entry, Quantity: event.target.value } : entry
                                    )),
                                  }))}
                                  onClick={event => event.stopPropagation()}
                                  className="block w-full bg-gray-700 text-white p-2 rounded-lg mt-1 border border-gray-600"
                                />
                              </div>
                              {option.Sources?.length > 0 && <p className="text-xs text-gray-500 mt-2">{t.mrpSources}</p>}
                              {option.Sources?.map((source, sourceIndex) => (
                                <div key={`${source.URL}-${sourceIndex}`} className="mt-2 text-xs">
                                  {source.URL ? (
                                    <a href={source.URL} target="_blank" rel="noreferrer" onClick={event => event.stopPropagation()} className="text-blue-400 underline">
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
                        onChange={event => setManualMrp(event.target.value)}
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
                  {pendingDraft.PriceOptions?.length === 0 && pendingDraft.SearchResults?.length > 0 && (
                    <div className="border-t border-gray-700 pt-3">
                      <p className="text-xs text-gray-400 font-semibold uppercase mb-2">{t.sourceLabel}</p>
                      <ul className="space-y-2">
                        {pendingDraft.SearchResults.map((source, index) => (
                          <li key={`${source.URL}-${index}`} className="text-xs">
                            {source.URL ? (
                              <a href={source.URL} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 underline">
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
                    <p role="alert" className="text-sm text-red-400">{confirmationError}</p>
                  )}
                </div>
                
                <div className="mt-8 flex space-x-3">
                  <button onClick={() => { setPendingDraft(null); setConfirmationError(''); }} className="w-1/3 py-3 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium transition-colors">
                    {t.cancelBtn}
                  </button>
                  <button
                    onClick={submitConfirmation}
                    disabled={!pendingDraft.ItemName.trim() || isSearchingProduct || !pendingDraft.PriceOptions?.some(option => option.Selected && Number(option.Quantity) > 0 && Number.isInteger(Number(option.Quantity)))}
                    className="w-2/3 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold shadow-lg shadow-blue-500/20 transition-all"
                  >
                    {t.confirmAddBtn}
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {pendingItemChoice && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4"
            >
              <motion.div
                initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }}
                className="bg-gray-800 border border-amber-500/50 p-6 rounded-2xl shadow-2xl w-full max-w-[440px] max-h-[85vh] overflow-y-auto"
              >
                <h3 className="text-xl font-bold text-white mb-2">{t.selectProductTitle}</h3>
                <p className="text-gray-400 text-sm mb-5">{t.selectProductDesc}</p>
                <p className="text-sm text-gray-300 mb-3">
                  {pendingItemChoice.Intent === 'sell' ? 'Sale' : 'Restock'} · {pendingItemChoice.Quantity}
                </p>
                <div className="space-y-2">
                  {pendingItemChoice.Candidates.map(item => (
                    <label
                      key={item.ItemID}
                      className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer ${
                        selectedItemId === item.ItemID
                          ? 'border-amber-400 bg-amber-400/10'
                          : 'border-gray-700 bg-gray-700/40'
                      }`}
                    >
                      <input
                        type="radio"
                        name="inventory-variant"
                        value={item.ItemID}
                        checked={selectedItemId === item.ItemID}
                        onChange={() => setSelectedItemId(item.ItemID)}
                        className="mt-1 accent-amber-400"
                      />
                      <span className="flex-1">
                        <span className="block font-semibold text-white">{item.ItemName}</span>
                        <span className="block text-sm text-gray-400">
                          ₹{Number(item.Price).toLocaleString('en-IN')} · {t.availableStock}: {item.StockQuantity}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
                {confirmationError && <p role="alert" className="text-sm text-red-400 mt-4">{confirmationError}</p>}
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => {
                      setPendingItemChoice(null);
                      setSelectedItemId(null);
                      setConfirmationError('');
                    }}
                    className="w-1/3 py-3 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium"
                  >
                    {t.cancelBtn}
                  </button>
                  <button
                    onClick={submitItemChoice}
                    disabled={selectedItemId === null}
                    className="flex-1 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold"
                  >
                    {t.confirmProduct}
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

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
                <motion.div className={`p-3 rounded-xl flex items-center space-x-3 border ${dbAction.status === 'success' ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300' : 'bg-blue-500/10 border-blue-500/40 text-blue-300'}`}>
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
              className="w-full max-w-5xl bg-gray-900/95 backdrop-blur-xl border border-gray-700 rounded-2xl p-8 shadow-2xl pointer-events-auto max-h-[85vh] overflow-y-auto"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white">{t.title}</h2>
                <button onClick={() => setLang(lang === 'en' ? 'hi' : 'en')} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium border border-gray-600 transition-colors">
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
                                <input type="text" className="bg-gray-700 text-white p-1 rounded text-sm w-full" value={editInvName} onChange={(e) => setEditInvName(e.target.value)} autoFocus />
                              ) : (item.ItemName)}
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
                                <input type="text" className="bg-gray-700 text-white p-1 rounded text-sm w-full" value={editCustName} onChange={(e) => setEditCustName(e.target.value)} autoFocus />
                              ) : (person.CustomerName)}
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

              {/* TRANSACTION LEDGER */}
              <section className="mt-8">
                <h3 className="text-lg font-semibold text-violet-400 mb-4">{t.ledgerTitle}</h3>
                <div className="bg-gray-800 rounded-xl overflow-auto border border-gray-700 max-h-80">
                  <table className="w-full min-w-[760px] text-left text-sm text-gray-300">
                    <thead className="bg-gray-700/70 text-gray-400 uppercase sticky top-0">
                      <tr>
                        <th className="px-4 py-3">{t.ledgerDate}</th>
                        <th className="px-4 py-3">{t.ledgerType}</th>
                        <th className="px-4 py-3">{t.ledgerEntity}</th>
                        <th className="px-4 py-3 text-right">{t.ledgerQuantity}</th>
                        <th className="px-4 py-3 text-right">{t.ledgerAmount}</th>
                        <th className="px-4 py-3">{t.ledgerDetails}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.length === 0 ? (
                        <tr>
                          <td colSpan="6" className="px-4 py-8 text-center text-gray-500">{t.ledgerEmpty}</td>
                        </tr>
                      ) : transactions.map((transaction) => (
                        <tr key={transaction.TxnID} className="border-t border-gray-700/50">
                          <td className="px-4 py-3 whitespace-nowrap">
                            {transaction.Timestamp
                              ? new Date(`${transaction.Timestamp.replace(' ', 'T')}Z`).toLocaleString()
                              : '—'}
                          </td>
                          <td className="px-4 py-3 font-medium text-white">{transaction.TransactionType}</td>
                          <td className="px-4 py-3">{transaction.EntityName || '—'}</td>
                          <td className="px-4 py-3 text-right">{transaction.Quantity ?? '—'}</td>
                          <td className="px-4 py-3 text-right whitespace-nowrap">
                            <span className={
                              transaction.TransactionType === 'Sale'
                                ? 'text-emerald-400'
                                : transaction.TransactionType === 'Restock'
                                  ? 'text-rose-400'
                                  : ''
                            }>
                              {transaction.TransactionType === 'Sale' ? '+' : ''}
                              {transaction.TransactionType === 'Restock' && Number(transaction.TotalAmount) < 0 ? '−' : ''}
                              ₹{Math.abs(Number(transaction.TotalAmount || 0)).toLocaleString('en-IN')}
                            </span>
                          </td>
                          <td className="px-4 py-3 max-w-xs truncate" title={transaction.CommandText || ''}>
                            {transaction.CommandText || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}