import { useState } from 'react';
import { api } from '../services/api';

/**
 * Custom hook managing manual inventory/credit forms, editing state,
 * and draft confirmation workflows (item choice, restock, removal).
 */
export function useStoreActions({
  t,
  onRefreshAll,
  playVoiceReceipt,
  setIsActive,
  setDbAction,
}) {
  // Modal / Draft states
  const [pendingDraft, setPendingDraft] = useState(null);
  const [pendingItemChoice, setPendingItemChoice] = useState(null);
  const [pendingRemoval, setPendingRemoval] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [confirmationError, setConfirmationError] = useState('');
  const [isSearchingProduct, setIsSearchingProduct] = useState(false);
  const [manualMrp, setManualMrp] = useState('');

  // Manual Add / Edit forms
  const [showAddInv, setShowAddInv] = useState(false);
  const [invForm, setInvForm] = useState({ ItemName: '', StockQuantity: '', Price: '' });
  const [showAddCust, setShowAddCust] = useState(false);
  const [custForm, setCustForm] = useState({ CustomerName: '', Amount: '0' });
  const [manualFormError, setManualFormError] = useState('');
  const [editInvId, setEditInvId] = useState(null);
  const [editInvName, setEditInvName] = useState('');
  const [editCustId, setEditCustId] = useState(null);
  const [editCustName, setEditCustName] = useState('');

  const handleAddInventory = async (e) => {
    e.preventDefault();
    setManualFormError('');
    try {
      await api.addInventory(invForm);
      setInvForm({ ItemName: '', StockQuantity: '', Price: '' });
      setShowAddInv(false);
      onRefreshAll();
    } catch (error) {
      console.error('Product add failed:', error);
      setManualFormError(error.message || t.connError);
    }
  };

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    setManualFormError('');
    try {
      await api.addCustomer(custForm);
      setCustForm({ CustomerName: '', Amount: '0' });
      setShowAddCust(false);
      onRefreshAll();
    } catch (error) {
      console.error('Customer add failed:', error);
      setManualFormError(error.message || t.connError);
    }
  };

  const handleEditInventory = async (id) => {
    try {
      await api.editInventory(id, editInvName);
      setEditInvId(null);
      onRefreshAll();
    } catch (error) {
      console.error('Inventory edit error:', error);
    }
  };

  const handleEditCustomer = async (id) => {
    try {
      await api.editCustomer(id, editCustName);
      setEditCustId(null);
      onRefreshAll();
    } catch (error) {
      console.error('Customer edit error:', error);
    }
  };

  const archiveEntity = async (entity) => {
    setConfirmationError('');
    try {
      const result = await api.archiveEntity({
        EntityType: entity.EntityType,
        EntityID: entity.EntityID,
        Reason: entity.Reason,
        RawCommand: entity.RawCommand,
      });
      setPendingRemoval(null);
      setConfirmationError('');
      setDbAction(result);
      if (setIsActive) setIsActive(Boolean(entity.RawCommand));
      onRefreshAll({ includeArchives: true });
      if (playVoiceReceipt) playVoiceReceipt(result.message);
      if (entity.RawCommand && setIsActive) {
        setTimeout(() => setIsActive(false), 5000);
      }
    } catch (error) {
      console.error('Entity removal failed:', error);
      setConfirmationError(error.message || t.connError);
    }
  };

  const submitConfirmation = async () => {
    setConfirmationError('');
    const selectedItems = (pendingDraft.PriceOptions || [])
      .filter((option) => option.Selected)
      .map((option) => ({ Price: option.Price, Quantity: option.Quantity }));
    if (!selectedItems.length) {
      setConfirmationError(t.chooseMrp);
      return;
    }
    try {
      const result = await api.confirmRestock({
        ItemName: pendingDraft.ItemName,
        Items: selectedItems,
        RawCommand: pendingDraft.RawCommand,
      });
      setPendingDraft(null);
      setManualMrp('');
      if (result.database_action?.message) {
        setDbAction(result.database_action);
        if (playVoiceReceipt) playVoiceReceipt(result.database_action.message);
      }
      onRefreshAll();
    } catch (error) {
      console.error('Product confirmation error:', error);
      setConfirmationError(error.message || t.connError);
    }
  };

  const submitItemChoice = async () => {
    if (!pendingItemChoice || selectedItemId === null) return;
    setConfirmationError('');
    try {
      const result = await api.confirmInventoryCommand({
        ItemID: selectedItemId,
        Intent: pendingItemChoice.Intent,
        Quantity: pendingItemChoice.Quantity,
        RawCommand: pendingItemChoice.RawCommand,
      });
      setPendingItemChoice(null);
      setSelectedItemId(null);
      setConfirmationError('');
      setDbAction(result.database_action);
      onRefreshAll();
    } catch (error) {
      console.error('Inventory variant confirmation error:', error);
      setConfirmationError(error.message || t.connError);
    }
  };

  const searchEditedProductName = async () => {
    if (!pendingDraft?.ItemName?.trim()) return;
    const requestedName = pendingDraft.ItemName.trim();
    setIsSearchingProduct(true);
    setConfirmationError('');
    setPendingDraft((current) =>
      current
        ? {
            ...current,
            Price: null,
            PriceFound: false,
            PriceIsMRP: false,
            SearchStatus: 'searching',
            SearchMessage: '',
            SearchResults: [],
            PriceOptions: [],
          }
        : current
    );

    try {
      const result = await api.lookupProduct(requestedName);
      setPendingDraft((current) =>
        current && current.ItemName.trim() === requestedName
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
          : current
      );
      if (result.SpeechMessage && playVoiceReceipt) {
        playVoiceReceipt(result.SpeechMessage);
      }
    } catch (error) {
      console.error('Product search error:', error);
      setConfirmationError(error.message || t.connError);
      setPendingDraft((current) =>
        current ? { ...current, SearchStatus: 'error', SearchResults: [] } : current
      );
    } finally {
      setIsSearchingProduct(false);
    }
  };

  const addManualMrp = () => {
    const price = Number(manualMrp);
    if (!(price > 0) || !Number.isFinite(price)) return;
    setPendingDraft((current) => {
      if (!current) return current;
      const options = current.PriceOptions || [];
      if (options.some((option) => Number(option.Price) === price)) {
        return {
          ...current,
          PriceOptions: options.map((option) =>
            Number(option.Price) === price ? { ...option, Selected: true } : option
          ),
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

  return {
    pendingDraft,
    setPendingDraft,
    pendingItemChoice,
    setPendingItemChoice,
    pendingRemoval,
    setPendingRemoval,
    selectedItemId,
    setSelectedItemId,
    confirmationError,
    setConfirmationError,
    isSearchingProduct,
    manualMrp,
    setManualMrp,
    showAddInv,
    setShowAddInv,
    invForm,
    setInvForm,
    showAddCust,
    setShowAddCust,
    custForm,
    setCustForm,
    manualFormError,
    editInvId,
    setEditInvId,
    editInvName,
    setEditInvName,
    editCustId,
    setEditCustId,
    editCustName,
    setEditCustName,
    handleAddInventory,
    handleAddCustomer,
    handleEditInventory,
    handleEditCustomer,
    archiveEntity,
    submitConfirmation,
    submitItemChoice,
    searchEditedProductName,
    addManualMrp,
  };
}

