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

export default function App() {
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
  const [credit, setCredit] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [hisaabData, setHisaabData] = useState(null);
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [showEvalModal, setShowEvalModal] = useState(false);
  const [showCallSimulator, setShowCallSimulator] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

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
    ({ includeArchives = false } = {}) => {
      fetchDashboardData();
      fetchLedgerData();
      if (includeArchives) fetchArchives();
    },
    [fetchArchives, fetchDashboardData, fetchLedgerData]
  );

  // Voice playback receipt hook
  const { voiceError, setVoiceError, playVoiceReceipt, stopActiveAudio } = useVoiceReceipt({
    playbackAudioContextRef: null,
    isMuted,
    lang,
  });

  // Store mutations, edits, and draft confirmations
  const actions = useStoreActions({
    t,
    onRefreshAll: refreshAll,
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
      actions.setPendingItemChoice(data.database_action.draft);
      actions.setSelectedItemId(null);
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
    onMicError: () => {
      setIsActive(true);
      setTranscript(t.micError);
      setTimeout(() => setIsActive(false), 3500);
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
      }
    };
    loadInitial();
    const interval = setInterval(fetchDashboardData, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
      stopActiveAudio();
    };
  }, [fetchDashboardData, stopActiveAudio]);

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

  return (
    <div className="flex flex-col w-screen h-screen relative bg-transparent overflow-hidden">
      <Header
        selectedLangCode={selectedLangCode}
        setSelectedLangCode={setSelectedLangCode}
        isMuted={isMuted}
        setIsMuted={setIsMuted}
        isRecording={voiceRecorder.isRecording}
        startRecording={voiceRecorder.startRecording}
        onOpenSimulator={() => setShowCallSimulator(true)}
        handleMinimize={handleMinimize}
        handleClose={handleClose}
      />

      <div className="flex-grow flex items-center justify-center p-6 pointer-events-none mt-10">
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

        {/* MODALS */}
        <CallSimulator
          isOpen={showCallSimulator}
          onClose={() => setShowCallSimulator(false)}
          onRefreshStore={refreshAll}
          existingCustomers={credit}
        />

        <BenchmarkModal
          showEvalModal={showEvalModal}
          onClose={() => setShowEvalModal(false)}
          benchmarkData={benchmarkData}
        />

        <ProductConfirmModal
          pendingDraft={actions.pendingDraft}
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
        />

        <ItemChoiceModal
          pendingItemChoice={actions.pendingItemChoice}
          selectedItemId={actions.selectedItemId}
          setSelectedItemId={actions.setSelectedItemId}
          confirmationError={actions.confirmationError}
          submitItemChoice={actions.submitItemChoice}
          onCancel={() => {
            actions.setPendingItemChoice(null);
            actions.setSelectedItemId(null);
            actions.setConfirmationError('');
          }}
          t={t}
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

        {/* MAIN DASHBOARD */}
        <AnimatePresence>
          {showDashboard && !showArchives && (
            <DashboardView
              t={t}
              lang={lang}
              setLang={setLang}
              selectedLangCode={selectedLangCode}
              setSelectedLangCode={setSelectedLangCode}
              isRecording={voiceRecorder.isRecording}
              startRecording={voiceRecorder.startRecording}
              onOpenSimulator={() => setShowCallSimulator(true)}
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
