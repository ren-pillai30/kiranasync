import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildReceiptEscPos, isBluetoothSupported } from './thermalPrinter.js';

test('isBluetoothSupported returns boolean in environment', () => {
  const supported = isBluetoothSupported();
  assert.strictEqual(typeof supported, 'boolean');
});

test('buildReceiptEscPos generates valid ESC/POS byte buffer for 58mm cash sale', () => {
  const billData = {
    storeName: 'Gupta Kirana Store',
    invoiceNo: 'KS-101',
    date: '02/11/2026',
    time: '15:45',
    customerName: 'Ramesh Kumar',
    paymentMode: 'cash',
    billItems: [
      { item_name: 'Tata Salt 1kg', quantity: 2, item_total: 56 },
      { item_name: 'Fortune Oil 1L', quantity: 1, item_total: 145 },
    ],
    subtotal: 201,
    grandTotal: 201,
    customerBalance: 0,
  };

  const buffer = buildReceiptEscPos(billData, { paperWidth: '58mm' });
  assert.ok(buffer instanceof Uint8Array);
  assert.ok(buffer.length > 50, 'Buffer should have substantial bytes');

  // Verify ESC @ (Init printer: 0x1B, 0x40) is at the beginning
  assert.strictEqual(buffer[0], 0x1b);
  assert.strictEqual(buffer[1], 0x40);

  // Convert buffer to string to check text content
  const decoder = new TextDecoder();
  const text = decoder.decode(buffer);

  assert.ok(text.includes('GUPTA KIRANA STORE'));
  assert.ok(text.includes('KS-101'));
  assert.ok(text.includes('Tata Salt 1kg'));
  assert.ok(text.includes('Fortune Oil 1L'));
  assert.ok(text.includes('201.00'));
});

test('buildReceiptEscPos includes udhaar details when paymentMode is udhaar', () => {
  const billData = {
    storeName: 'Apna Bazar',
    invoiceNo: 'KS-102',
    date: '02/11/2026',
    time: '15:46',
    customerName: 'Suresh Bhai',
    paymentMode: 'udhaar',
    billItems: [{ item_name: 'Aashirvaad Atta 5kg', quantity: 1, item_total: 240 }],
    subtotal: 240,
    grandTotal: 240,
    customerBalance: 500,
  };

  const buffer = buildReceiptEscPos(billData, { paperWidth: '80mm' });
  const decoder = new TextDecoder();
  const text = decoder.decode(buffer);

  assert.ok(text.includes('Previous Udhaar:'));
  assert.ok(text.includes('Total Udhaar Baaki:'));
  assert.ok(text.includes('740.00')); // 500 + 240
});
