import { useState } from 'react';
import { api } from '../services/api';

/**
 * Custom hook managing manual inventory/credit forms, editing state,
 * and draft confirmation workflows (item choice, restock, removal).
 */
export function useStoreActions({
  t,
  inventory = [],
  onRefreshAll,
  onInventoryUpdated,
  playVoiceReceipt,
  setIsActive,
  setDbAction,
}) {
  // Modal / Draft states
  const [pendingDraft, setPendingDraft] = useState(null);
  const [pendingItemChoice, setPendingItemChoice] = useState(null);
  const [pendingRemoval, setPendingRemoval] = useState(null);
  const [pendingTransaction, setPendingTransaction] = useState(null);
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [confirmationError, setConfirmationError] = useState('');
  const [isSearchingProduct, setIsSearchingProduct] = useState(false);
  const [manualMrp, setManualMrp] = useState('');

  // Manual Add / Edit forms
  const [showAddInv, setShowAddInv] = useState(false);
  const [invForm, setInvForm] = useState({ ItemName: '', ItemNameHindi: '', StockQuantity: '', Price: '' });
  const [showAddCust, setShowAddCust] = useState(false);
  const [custForm, setCustForm] = useState({ CustomerName: '', CustomerNameHindi: '', Amount: '0' });
  const [manualFormError, setManualFormError] = useState('');
  const [editInvId, setEditInvId] = useState(null);
  const [editInvName, setEditInvName] = useState('');
  const [editInvNameHindi, setEditInvNameHindi] = useState('');
  const [editCustId, setEditCustId] = useState(null);
  const [editCustName, setEditCustName] = useState('');
  const [editCustNameHindi, setEditCustNameHindi] = useState('');

  const handleAddInventory = async (e) => {
    e.preventDefault();
    setManualFormError('');
    const normalizeProductName = (name) =>
      String(name || '')
        .replace(/\s*\(MRP\s*₹?\s*[\d,.]+\)\s*$/i, '')
        .normalize('NFKC')
        .trim()
        .toLocaleLowerCase();
    const requestedName = normalizeProductName(invForm.ItemName);
    const matches = inventory.filter((item) =>
      [item.ItemName, item.ItemNameHindi].some(
        (name) => requestedName && normalizeProductName(name) === requestedName
      )
    );
    const requestedPrice = Number(invForm.Price);
    const priceMatch = matches.find(
      (item) => Number(item.Price) === requestedPrice
    );
    const existing = priceMatch || (matches.length === 1 ? matches[0] : null);
    if (matches.length > 1 && !priceMatch) {
      setPendingItemChoice({
        Intent: 'restock',
        Quantity: Number(invForm.StockQuantity),
        EntityName: invForm.ItemName,
        Candidates: matches,
        AllowNewProduct: false,
        Source: 'manual_add',
        RequestedPrice: requestedPrice,
        RawCommand: `Manual add ${invForm.ItemName}`,
      });
      setSelectedItemId(null);
      setConfirmationError('');
      return;
    }
    if (existing) {
      setPendingTransaction({
        Intent: 'restock',
        ItemID: existing.ItemID,
        ItemName: existing.ItemName,
        Quantity: Number(invForm.StockQuantity),
        CurrentStock: Number(existing.StockQuantity),
        ExistingPrice: Number(existing.Price),
        RequestedPrice: Number(invForm.Price),
        StockMode: 'add',
        Source: 'manual_add',
        RawCommand: `Manual add ${invForm.ItemName}`,
      });
      setConfirmationError('');
      return;
    }
    setPendingDraft({
      ItemName: invForm.ItemName.trim(),
      ItemNameHindi: invForm.ItemNameHindi.trim(),
      StockQuantity: Number(invForm.StockQuantity),
      Price: null,
      PriceOptions: [],
      SearchStatus: 'idle',
      RawCommand: `Manual add ${invForm.ItemName.trim()}`,
      Source: 'manual_add',
      ManualPrice: requestedPrice,
    });
    setManualMrp('');
  };

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    setManualFormError('');
    try {
      await api.addCustomer(custForm);
      setCustForm({ CustomerName: '', CustomerNameHindi: '', Amount: '0' });
      setShowAddCust(false);
      onRefreshAll();
    } catch (error) {
      console.error('Customer add failed:', error);
      setManualFormError(error.message || t.connError);
    }
  };

  const handleEditInventory = async (id) => {
    try {
      const result = await api.editInventory(id, editInvName, editInvNameHindi);
      setEditInvId(null);
      onInventoryUpdated?.(result.item);
    } catch (error) {
      console.error('Inventory edit error:', error);
    }
  };

  const handleEditCustomer = async (id) => {
    try {
      await api.editCustomer(id, editCustName, editCustNameHindi);
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
      if (pendingDraft.Source === 'manual_add') {
        setInvForm({ ItemName: '', ItemNameHindi: '', StockQuantity: '', Price: '' });
        setShowAddInv(false);
      }
      if (result.database_action?.message) {
        setDbAction(result.database_action);
        if (playVoiceReceipt) playVoiceReceipt(result.database_action.message);
      }
      for (const item of result.items || []) {
        onInventoryUpdated?.(item);
      }
      onRefreshAll();
    } catch (error) {
      console.error('Product confirmation error:', error);
      setConfirmationError(error.message || t.connError);
    }
  };

  const handleAddNewProductFromChoice = async (entityName, quantity = 1) => {
    const rawCmd = pendingItemChoice?.RawCommand || '';
    setPendingItemChoice(null);
    setSelectedItemId(null);
    setConfirmationError('');

    const draft = {
      ItemName: entityName || '',
      StockQuantity: quantity || 1,
      Price: null,
      PriceOptions: [],
      RawCommand: rawCmd,
      SearchStatus: 'idle',
      SearchResults: [],
    };
    setPendingDraft(draft);
    setManualMrp('');

    if (entityName && entityName.trim()) {
      setIsSearchingProduct(true);
      try {
        const result = await api.lookupProduct(entityName.trim());
        setPendingDraft((current) => ({
          ...current,
          ...result,
          StockQuantity: quantity || 1,
          RawCommand: rawCmd,
          PriceOptions: (result.PriceOptions || []).map((option, index) => ({
            ...option,
            Quantity: quantity || 1,
            Selected: index === 0,
          })),
        }));
      } catch (err) {
        console.warn('Product lookup failed on new choice:', err);
      } finally {
        setIsSearchingProduct(false);
      }
    }
  };

  const submitItemChoice = async () => {
    if (!pendingItemChoice || selectedItemId === null) return;
    setConfirmationError('');
    if (pendingItemChoice.Intent === 'restock') {
      const selectedItem = pendingItemChoice.Candidates.find(
        (item) => item.ItemID === selectedItemId
      );
      if (!selectedItem) return;
      setPendingTransaction({
        Intent: 'restock',
        ItemID: selectedItem.ItemID,
        ItemName: selectedItem.ItemName,
        Quantity: pendingItemChoice.Quantity,
        CurrentStock: selectedItem.StockQuantity,
        StockMode: 'add',
        Source: pendingItemChoice.Source,
        RequestedPrice: pendingItemChoice.RequestedPrice,
        ExistingPrice: selectedItem.Price,
        RawCommand: pendingItemChoice.RawCommand,
      });
      setPendingItemChoice(null);
      setSelectedItemId(null);
      return;
    }
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
      if (result.item) onInventoryUpdated?.(result.item);
      onRefreshAll();
    } catch (error) {
      console.error('Inventory variant confirmation error:', error);
      setConfirmationError(error.message || t.connError);
    }
  };

  const confirmTransaction = async () => {
    if (!pendingTransaction) return;
    setConfirmationError('');
    try {
      const result = pendingTransaction.Intent === 'credit'
        ? await api.confirmTransaction(pendingTransaction)
        : await api.confirmInventoryCommand(pendingTransaction);
      setPendingTransaction(null);
      setDbAction(result.database_action);
      if (playVoiceReceipt) playVoiceReceipt(result.database_action.message);
      if (result.item) onInventoryUpdated?.(result.item);
      if (pendingTransaction.Source === 'manual_add') {
        setInvForm({ ItemName: '', ItemNameHindi: '', StockQuantity: '', Price: '' });
        setShowAddInv(false);
      }
      onRefreshAll();
    } catch (error) {
      console.error('Transaction confirmation failed:', error);
      setConfirmationError(error.message || t.connError);
    }
  };

  const searchEditedProductName = async () => {
    if (!pendingDraft?.ItemName?.trim()) return;
    const requestedName = pendingDraft.ItemName.trim();
    const manualPrice = Number(pendingDraft.ManualPrice);
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
              PriceOptions: [
                ...(result.PriceOptions || []).map((option, index) => ({
                  ...option,
                  Quantity: current.StockQuantity,
                  Selected: index === 0,
                })),
                ...(Number.isFinite(manualPrice) &&
                manualPrice > 0 &&
                !(result.PriceOptions || []).some(
                  (option) => Number(option.Price) === manualPrice
                )
                  ? [{
                      Price: manualPrice,
                      PriceIsMRP: false,
                      IsManual: true,
                      Sources: [],
                      Quantity: current.StockQuantity,
                      Selected: !(result.PriceOptions || []).length,
                    }]
                  : []),
              ],
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
        current
          ? {
              ...current,
              SearchStatus: 'error',
              SearchResults: [],
              PriceOptions:
                Number.isFinite(manualPrice) && manualPrice > 0
                  ? [{
                      Price: manualPrice,
                      PriceIsMRP: false,
                      IsManual: true,
                      Sources: [],
                      Quantity: current.StockQuantity,
                      Selected: true,
                    }]
                  : current.PriceOptions,
            }
          : current
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
    pendingTransaction,
    setPendingTransaction,
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
    editInvNameHindi,
    setEditInvNameHindi,
    editCustId,
    setEditCustId,
    editCustName,
    setEditCustName,
    editCustNameHindi,
    setEditCustNameHindi,
    handleAddInventory,
    handleAddCustomer,
    handleEditInventory,
    handleEditCustomer,
    archiveEntity,
    submitConfirmation,
    submitItemChoice,
    confirmTransaction,
    handleAddNewProductFromChoice,
    searchEditedProductName,
    addManualMrp,
  };
}
