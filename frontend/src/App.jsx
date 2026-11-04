import { useState, useEffect, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';

import { text } from './constants/localization';
import { api } from './services/api';
import { useVoiceRecorder } from './hooks/useVoiceRecorder';
import { useVoiceReceipt } from './hooks/useVoiceReceipt';
import { useStoreActions } from './hooks/useStoreActions';

import Header from './components/Header';
import VoiceRecordingHud from './components/VoiceRecordingHud';
import DashboardView from './components/DashboardView';
import CallSimulator from './components/CallSimulator';

import ProductConfirmModal from './components/modals/ProductConfirmModal';
import ItemChoiceModal from './components/modals/ItemChoiceModal';
import EntityRemovalModal from './components/modals/EntityRemovalModal';
import ArchivesModal from './components/modals/ArchivesModal';
import BenchmarkModal from './components/modals/BenchmarkModal';
import BillModal from './components/modals/BillModal';
import DayClosingModal from './components/modals/DayClosingModal';
import BarcodeScannerModal from './components/modals/BarcodeScannerModal';
import FeedbackModal from './components/modals/FeedbackModal';
import TransactionConfirmModal from './components/modals/TransactionConfirmModal';
import AuthScreen from './components/AuthScreen';
import StoreSetupModal from './components/modals/StoreSetupModal';

export default function App() {
  const [authChecked, setAuthChecked] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [storeSetupComplete, setStoreSetupComplete] = useState(true);
  const [storeSession, setStoreSession] = useState(null);
  const [lang, setLang] = useState('en');
  const [selectedLangCode, setSelectedLangCode] = useState('hi-IN');
  const t = text[lang];

  const [isActive, setIsActive] = useState(false);
  const [showDashboard, setShowDashboard] = useState(true);
  const [showArchives, setShowArchives] = useState(false);
  const [archives, setArchives] = useState([]);
  const [archivesError, setArchivesError] = useState('');
  const [transcript, setTranscript] = useState(t.defaultListening);
  const [dbAction, setDbAction] = useState(null);

  // Store financial & inventory data
  const [inventory, setInventory] = useState([]);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [credit, setCredit] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [hisaabData, setHisaabData] = useState(null);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [showEvalModal, setShowEvalModal] = useState(false);
  const [showCallSimulator, setShowCallSimulator] = useState(false);
  const [showBillModal, setShowBillModal] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [showDayClosingModal, setShowDayClosingModal] = useState(false);
  const [showBarcodeModal, setShowBarcodeModal] = useState(false);
  const [barcodeNotice, setBarcodeNotice] = useState('');
  const [billData, setBillData] = useState({ billItems: [], customerName: 'Walk-in Customer', paymentMode: 'cash', customerBalance: 0 });
  const [isMuted, setIsMuted] = useState(false);
  const [nameDisplayMode, setNameDisplayMode] = useState(() => (
    typeof window !== 'undefined' ? window.localStorage.getItem('kiranasync-name-display') || 'en' : 'en'
  ));

  const handleLanguageChange = useCallback((nextLang) => {
    const normalized = nextLang === 'hi' ? 'hi' : 'en';
    setLang(normalized);
    setNameDisplayMode(normalized);
    setSelectedLangCode(normalized === 'hi' ? 'hi-IN' : 'en-IN');
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('kiranasync-name-display', nameDisplayMode);
    }
  }, [nameDisplayMode]);

  const checkAuth = useCallback(async () => {
    try {
      const session = await api.getAuthSession();
      setAuthenticated(true);
      setStoreSetupComplete(session.user.store_setup_complete !== false);
      setStoreSession(session.user);
    } catch {
      setAuthenticated(false);
    } finally {
      setAuthChecked(true);
    }
  }, []);

  useEffect(() => {
    const initializeAuth = async () => {
      await checkAuth();
    };
    void initializeAuth();
  }, [checkAuth]);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [data, hisaab] = await Promise.all([api.getDashboard(), api.getHisaab()]);
      if (data.status === 'success') {
        setInventory(data.inventory);
        setCredit(data.credit);
      }
      if (hisaab.status === 'success') {
        setHisaabData(hisaab);
      }
    } catch (error) {
      console.error('Dashboard fetch error:', error);
    }
  }, []);

  const fetchLedgerData = useCallback(async () => {
    try {
      const data = await api.getLedger();
      if (data.status === 'success') {
        setTransactions(data.transactions);
      }
    } catch (error) {
      console.error('Transaction ledger fetch error:', error);
    }
  }, []);

  const fetchArchives = useCallback(async () => {
    try {
      const data = await api.getArchives();
      setArchives(data.archives);
      setArchivesError('');
    } catch (error) {
      console.error('Archive audit fetch error:', error);
      setArchivesError(error.message || 'Could not load archive audit records.');
    }
  }, []);

  const refreshAll = useCallback(
    async ({ includeArchives = false } = {}) => {
      await Promise.all([
        fetchDashboardData(),
        fetchLedgerData(),
        includeArchives ? fetchArchives() : Promise.resolve(),
      ]);
    },
    [fetchArchives, fetchDashboardData, fetchLedgerData]
  );

  // Voice playback receipt hook
  const { voiceError, setVoiceError, playVoiceReceipt, stopActiveAudio } = useVoiceReceipt({
    playbackAudioContextRef: null,
    isMuted,
    lang,
    inventory,
    credit,
  });

  // Store mutations, edits, and draft confirmations
  const actions = useStoreActions({
    t,
    onRefreshAll: refreshAll,
    onInventoryUpdated: (updatedItem) => {
      setInventory((current) => {
        const existingIndex = current.findIndex((item) => item.ItemID === updatedItem.ItemID);
        if (existingIndex === -1) return [...current, updatedItem];
        return current.map((item) => item.ItemID === updatedItem.ItemID ? updatedItem : item);
      });
    },
    playVoiceReceipt,
    setIsActive,
    setDbAction,
  });

  const handleVoiceSuccess = useCallback((data) => {
    setTranscript(data.transcript);
    if (data.database_action?.status === 'success') {
      fetchDashboardData();
      fetchLedgerData();
    }

    if (
      data.database_action?.message &&
      [
        'query_stock',
        'query_customer',
        'customer_archived',
        'customer_deleted',
        'inventory_archived',
        'measurement_mismatch',
      ].includes(data.database_action.action)
    ) {
      playVoiceReceipt(data.database_action.speech_message || data.database_action.message);
    }
    if (['customer_archived', 'customer_deleted', 'inventory_archived'].includes(data.database_action?.action)) {
      fetchArchives();
    }

    if (data.database_action && data.database_action.status === 'pending_confirmation') {
      const draft = data.database_action.draft;
      if (draft?.Intent && ['sell', 'restock', 'credit'].includes(draft.Intent)) {
        playVoiceReceipt(data.database_action.message);
        actions.setPendingTransaction(draft);
        actions.setConfirmationError('');
        setDbAction({ status: 'pending', message: data.database_action.message });
        setTimeout(() => setIsActive(false), 2500);
        return;
      }
      if (draft?.EntityType) {
        playVoiceReceipt(data.database_action.message);
        actions.setPendingRemoval(draft);
        actions.setConfirmationError('');
        setDbAction({ status: 'pending', message: data.database_action.message });
        return;
      }
      if (draft?.ItemName) {
        playVoiceReceipt(data.database_action.speech_message || data.database_action.message);
      }
      const options =
        draft.PriceOptions ||
        (Number(draft.Price) > 0
          ? [{ Price: Number(draft.Price), PriceIsMRP: draft.PriceIsMRP, Sources: [] }]
          : []);
      actions.setPendingDraft({
        ...draft,
        PriceOptions: options.map((option, index) => ({
          ...option,
          Quantity: draft.StockQuantity,
          Selected: index === 0,
        })),
      });
      actions.setManualMrp('');
      actions.setConfirmationError('');
      setDbAction({ status: 'pending', message: data.database_action.message });
      setTimeout(() => setIsActive(false), 2500);
    } else if (data.database_action?.status === 'pending_selection') {
      if (data.database_action?.message) {
        playVoiceReceipt(data.database_action.speech_message || data.database_action.message);
      }
      const draft = data.database_action.draft;
      actions.setPendingItemChoice(draft);
      actions.setSelectedItemId(
        draft.NearestMatch && draft.Candidates?.length === 1
          ? draft.Candidates[0].ItemID
          : null
      );
      actions.setConfirmationError('');
      setDbAction({ status: 'pending', message: data.database_action.message });
      setTimeout(() => setIsActive(false), 2500);
    } else {
      setDbAction(data.database_action);
      setTimeout(() => setIsActive(false), 5000);
    }
  }, [actions, fetchArchives, fetchDashboardData, fetchLedgerData, playVoiceReceipt]);

  const voiceRecorder = useVoiceRecorder({
    selectedLangCode,
    onSpeechDetected: () => {
      setIsActive(true);
      setVoiceError('');
      setTranscript(t.defaultListening);
      setDbAction(null);
    },
    onProcessing: () => setTranscript(t.processing),
    onSuccess: handleVoiceSuccess,
    onError: (errMsg) => {
      setTranscript(`Notice: ${errMsg}`);
      setTimeout(() => setIsActive(false), 4000);
    },
  });

  useEffect(() => {
    let isMounted = true;
    const loadInitial = async () => {
      try {
        const [dashData, ledgData, hisaabJson] = await Promise.all([
          api.getDashboard(),
          api.getLedger(),
          api.getHisaab(),
        ]);
        if (isMounted) {
          if (dashData.status === 'success') {
            setInventory(dashData.inventory);
            setCredit(dashData.credit);
          }
          if (ledgData.status === 'success') {
            setTransactions(ledgData.transactions);
          }
          if (hisaabJson.status === 'success') {
            setHisaabData(hisaabJson);
          }
        }
      } catch (err) {
        console.warn('Initial data load error:', err);
      } finally {
        if (isMounted) setDashboardLoading(false);
      }
    };
    loadInitial();
    return () => {
      isMounted = false;
      stopActiveAudio();
    };
  }, [fetchDashboardData, stopActiveAudio]);

  const handleQuickSellFromBarcode = (item) => {
    actions.setPendingTransaction({
      Intent: 'sell',
      ItemID: item.ItemID,
      ItemName: item.ItemName,
      Quantity: 1,
      CurrentStock: item.StockQuantity,
      RawCommand: `Barcode Quick Sale: 1x ${item.ItemName}`,
    });
  };

  const handleOpenBill = (data = {}) => {
    setBillData({
      billItems: data.billItems || (inventory.length > 0 ? [
        {
          item_name: inventory[0].ItemName,
          quantity: 1,
          unit_price: Number(inventory[0].Price || 0),
          item_total: Number(inventory[0].Price || 0),
        }
      ] : []),
      customerName: data.customerName || 'Walk-in Customer',
      paymentMode: data.paymentMode || 'cash',
      customerBalance: data.customerBalance || 0,
    });
    setShowBillModal(true);
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

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-full max-w-md px-6">
          <div className="h-10 w-10 mx-auto animate-pulse rounded-full border-2 border-white/70 border-t-transparent" />
          <div className="mt-6 space-y-3">
            <div className="h-3 rounded-full bg-white/10 animate-pulse" />
            <div className="h-3 w-4/5 mx-auto rounded-full bg-white/10 animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (!authenticated) {
    return <AuthScreen onAuthenticated={(session) => {
      setAuthenticated(true);
      setStoreSetupComplete(session?.user?.store_setup_complete !== false);
      setStoreSession(session?.user || null);
    }} />;
  }

  return (
    <div className="flex flex-col w-screen h-screen relative bg-transparent overflow-hidden">
      {!storeSetupComplete && (
        <StoreSetupModal
          initialStore={storeSession}
          onComplete={() => setStoreSetupComplete(true)}
        />
      )}
      <Header
        selectedLangCode={selectedLangCode}
        setSelectedLangCode={(languageCode) => {
          setSelectedLangCode(languageCode);
          handleLanguageChange(languageCode.startsWith('hi') ? 'hi' : 'en');
        }}
        isMuted={isMuted}
        setIsMuted={setIsMuted}
        isRecording={voiceRecorder.isRecording}
        startRecording={voiceRecorder.startRecording}
        onOpenSimulator={() => setShowCallSimulator(true)}
        onOpenBill={() => handleOpenBill()}
        onOpenFeedback={() => setShowFeedbackModal(true)}
        onOpenDayClosing={() => setShowDayClosingModal(true)}
        onOpenBarcode={() => {
          setShowBarcodeModal(true);
          setBarcodeNotice(typeof window !== 'undefined' && 'BarcodeDetector' in window ? '' : 'Barcode scanning is not supported in this browser; manual entry still works.');
        }}
        handleMinimize={handleMinimize}
        handleClose={handleClose}
      />

      {/* INTERACTIVE MODALS & VOICE HUD */}
      <div className="pointer-events-auto">
        <CallSimulator
          isOpen={showCallSimulator}
          onClose={() => setShowCallSimulator(false)}
          onRefreshStore={refreshAll}
          onOpenBill={(data) => handleOpenBill(data)}
          existingCustomers={credit}
          nameDisplayMode={nameDisplayMode}
        />

        <BillModal
          isOpen={showBillModal}
          onClose={() => setShowBillModal(false)}
          billItems={billData.billItems}
          customerName={billData.customerName}
          paymentMode={billData.paymentMode}
          customerBalance={billData.customerBalance}
        />

        <FeedbackModal
          isOpen={showFeedbackModal}
          onClose={() => setShowFeedbackModal(false)}
        />

        <DayClosingModal
          isOpen={showDayClosingModal}
          onClose={() => setShowDayClosingModal(false)}
          hisaabData={hisaabData}
        />

        <BarcodeScannerModal
          isOpen={showBarcodeModal}
          onClose={() => setShowBarcodeModal(false)}
          inventory={inventory}
          nameDisplayMode={nameDisplayMode}
          onAddToBill={(data) => handleOpenBill(data)}
          onQuickSell={handleQuickSellFromBarcode}
          onRefreshAll={refreshAll}
          barcodeNotice={barcodeNotice}
          setBarcodeNotice={setBarcodeNotice}
        />

        <BenchmarkModal
          showEvalModal={showEvalModal}
          onClose={() => setShowEvalModal(false)}
          benchmarkData={benchmarkData}
        />

        <ProductConfirmModal
          pendingDraft={actions.pendingDraft}
          nameDisplayMode={nameDisplayMode}
          setPendingDraft={actions.setPendingDraft}
          confirmationError={actions.confirmationError}
          setConfirmationError={actions.setConfirmationError}
          isSearchingProduct={actions.isSearchingProduct}
          manualMrp={actions.manualMrp}
          setManualMrp={actions.setManualMrp}
          searchEditedProductName={actions.searchEditedProductName}
          addManualMrp={actions.addManualMrp}
          submitConfirmation={actions.submitConfirmation}
          onCancel={() => {
            actions.setPendingDraft(null);
            actions.setConfirmationError('');
          }}
          t={t}
          nameDisplayMode={nameDisplayMode}
        />

        <ItemChoiceModal
          pendingItemChoice={actions.pendingItemChoice}
          selectedItemId={actions.selectedItemId}
          setSelectedItemId={actions.setSelectedItemId}
          confirmationError={actions.confirmationError}
          submitItemChoice={actions.submitItemChoice}
          onAddNewProduct={actions.handleAddNewProductFromChoice}
          onCancel={() => {
            actions.setPendingItemChoice(null);
            actions.setSelectedItemId(null);
            actions.setConfirmationError('');
          }}
          t={t}
          nameDisplayMode={nameDisplayMode}
        />

        <TransactionConfirmModal
          pendingTransaction={actions.pendingTransaction}
          inventory={inventory}
          credit={credit}
          nameDisplayMode={nameDisplayMode}
          confirmationError={actions.confirmationError}
          onConfirm={actions.confirmTransaction}
          onCancel={() => {
            actions.setPendingTransaction(null);
            actions.setConfirmationError('');
          }}
        />

        <EntityRemovalModal
          pendingRemoval={actions.pendingRemoval}
          setPendingRemoval={actions.setPendingRemoval}
          confirmationError={actions.confirmationError}
          confirmEntityRemoval={() => {
            if (actions.pendingRemoval) actions.archiveEntity(actions.pendingRemoval);
          }}
          onCancel={() => {
            actions.setPendingRemoval(null);
            actions.setConfirmationError('');
          }}
        />

        <VoiceRecordingHud
          isActive={isActive}
          isRecording={voiceRecorder.isRecording}
          lang={lang}
          audioLevel={voiceRecorder.audioLevel}
          transcript={transcript}
          dbAction={dbAction}
          voiceError={voiceError}
          t={t}
          stopAndProcessRecording={voiceRecorder.stopAndProcessRecording}
        />
      </div>

      <div className="flex-grow min-h-0 flex items-start sm:items-center justify-center p-2 sm:p-6 pointer-events-none overflow-hidden">
        <button id="voice-trigger" onClick={voiceRecorder.startRecording} className="hidden">
          Voice
        </button>
        <button
          id="dashboard-trigger"
          onClick={() => setShowDashboard(!showDashboard)}
          className="hidden"
        >
          Dash
        </button>

        {/* MAIN DASHBOARD */}
        <AnimatePresence>
          {showDashboard && !showArchives && (
            <DashboardView
              t={t}
              lang={lang}
              setLang={setLang}
              onLanguageChange={handleLanguageChange}
              selectedLangCode={selectedLangCode}
              setSelectedLangCode={setSelectedLangCode}
              isRecording={voiceRecorder.isRecording}
              startRecording={voiceRecorder.startRecording}
              onOpenSimulator={() => setShowCallSimulator(true)}
              onOpenBill={() => handleOpenBill()}
              onOpenFeedback={() => setShowFeedbackModal(true)}
              onOpenDayClosing={() => setShowDayClosingModal(true)}
              onOpenBarcode={() => {
                setShowBarcodeModal(true);
                setBarcodeNotice(typeof window !== 'undefined' && 'BarcodeDetector' in window ? '' : 'Barcode scanning is not supported in this browser; manual entry still works.');
              }}
              onViewBill={(data) => handleOpenBill(data)}
              onOpenEvalModal={async () => {
                try {
                  const data = await api.getBenchmark();
                  setBenchmarkData(data);
                  setShowEvalModal(true);
                } catch {
                  alert('Evaluation service unavailable.');
                }
              }}
              onOpenArchives={() => {
                setShowArchives(true);
                fetchArchives();
              }}
              hisaabData={hisaabData}
              inventory={inventory}
              dashboardLoading={dashboardLoading}
              showAddInv={actions.showAddInv}
              setShowAddInv={actions.setShowAddInv}
              invForm={actions.invForm}
              setInvForm={actions.setInvForm}
              manualFormError={actions.manualFormError}
              handleAddInventory={actions.handleAddInventory}
              editInvId={actions.editInvId}
              setEditInvId={actions.setEditInvId}
              editInvName={actions.editInvName}
              setEditInvName={actions.setEditInvName}
              handleEditInventory={actions.handleEditInventory}
              onRequestRemoval={(removal) => {
                actions.setConfirmationError('');
                actions.setPendingRemoval(removal);
              }}
              credit={credit}
              showAddCust={actions.showAddCust}
              setShowAddCust={actions.setShowAddCust}
              custForm={actions.custForm}
              setCustForm={actions.setCustForm}
              handleAddCustomer={actions.handleAddCustomer}
              editCustId={actions.editCustId}
              setEditCustId={actions.setEditCustId}
              editCustName={actions.editCustName}
              setEditCustName={actions.setEditCustName}
              handleEditCustomer={actions.handleEditCustomer}
              onDirectArchive={actions.archiveEntity}
              transactions={transactions}
              nameDisplayMode={nameDisplayMode}
              setNameDisplayMode={setNameDisplayMode}
              editInvNameHindi={actions.editInvNameHindi}
              setEditInvNameHindi={actions.setEditInvNameHindi}
              editCustNameHindi={actions.editCustNameHindi}
              setEditCustNameHindi={actions.setEditCustNameHindi}
            />
          )}

          {/* REMOVAL ARCHIVES AUDIT MODAL */}
          <ArchivesModal
            showArchives={showDashboard && showArchives}
            onClose={() => setShowArchives(false)}
            archives={archives}
            archivesError={archivesError}
            lang={lang}
          />
        </AnimatePresence>
      </div>
    </div>
  );
}
