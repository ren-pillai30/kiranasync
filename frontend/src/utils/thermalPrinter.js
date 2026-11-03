/**
 * KiranaSync ESC/POS Web Bluetooth Thermal Printer Engine
 * Supports standard 58mm (32 chars/line) and 80mm (48 chars/line) thermal POS receipt printers
 * (TVS, NGX, Everycom, BluPrint, Posiflex, Epson, Xprinter, etc.)
 */

// Common Bluetooth Printer Service UUIDs
const PRINTER_SERVICES = [
  '000018f0-0000-1000-8000-00805f9b34fb', // Standard POS Printer Service
  'e7810a71-73ae-499d-8c15-faa9aef0c3f2', // Posiflex / Common Chinese BLE
  '49535343-fe7d-4ae5-8fa9-9fafd205e455', // ISSC Transparent / TVS / NGX
  '0000af30-0000-1000-8000-00805f9b34fb', // Custom Mini POS
  '0000ff00-0000-1000-8000-00805f9b34fb', // Generic BLE SPP
];

// ESC/POS Command Byte Constants
const ESC = 0x1b;
const GS = 0x1d;

const CMD = {
  INIT: [ESC, 0x40], // Initialize printer
  ALIGN_LEFT: [ESC, 0x61, 0],
  ALIGN_CENTER: [ESC, 0x61, 1],
  ALIGN_RIGHT: [ESC, 0x61, 2],
  BOLD_ON: [ESC, 0x45, 1],
  BOLD_OFF: [ESC, 0x45, 0],
  DOUBLE_SIZE: [GS, 0x21, 0x11], // 2x width & 2x height
  DOUBLE_WIDTH: [GS, 0x21, 0x20],
  NORMAL_SIZE: [GS, 0x21, 0x00],
  FEED_LINE: [0x0a],
  FEED_AND_CUT: [GS, 0x56, 0x42, 0x00], // Full cut with feed
};

/**
 * Check if Web Bluetooth API is supported in the current browser environment
 */
export function isBluetoothSupported() {
  return typeof navigator !== 'undefined' && 'bluetooth' in navigator;
}

/**
 * Pads a string with spaces to align columns
 */
function padRow(col1, col2, width = 32) {
  const c1 = String(col1 || '');
  const c2 = String(col2 || '');
  const spaceCount = Math.max(1, width - c1.length - c2.length);
  return c1 + ' '.repeat(spaceCount) + c2;
}

/**
 * Build ESC/POS formatted binary buffer for Kirana receipt
 */
export function buildReceiptEscPos(billData, { paperWidth = '58mm' } = {}) {
  const colWidth = paperWidth === '80mm' ? 48 : 32;
  const divider = '-'.repeat(colWidth);
  const doubleDivider = '='.repeat(colWidth);

  const {
    storeName = 'KIRANASYNC STORE',
    invoiceNo = 'INV-001',
    date = new Date().toLocaleDateString('en-IN'),
    time = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
    customerName = 'Walk-in Customer',
    paymentMode = 'cash',
    billItems = [],
    subtotal = 0,
    grandTotal = 0,
    customerBalance = 0,
  } = billData;

  const encoder = new TextEncoder();
  const byteArrays = [];

  const addBytes = (bytes) => {
    byteArrays.push(new Uint8Array(bytes));
  };

  const addText = (text) => {
    byteArrays.push(encoder.encode(text));
  };

  const addLine = (text) => {
    addText(text + '\n');
  };

  // 1. Initialize
  addBytes(CMD.INIT);

  // 2. Header
  addBytes(CMD.ALIGN_CENTER);
  addBytes(CMD.BOLD_ON);
  addBytes(CMD.DOUBLE_SIZE);
  addLine(storeName.toUpperCase());
  addBytes(CMD.NORMAL_SIZE);
  addBytes(CMD.BOLD_OFF);
  addLine('Kirana Digital Counter POS');
  addLine('Near Main Road, Market Area');
  addLine(divider);

  // 3. Metadata
  addBytes(CMD.ALIGN_LEFT);
  addLine(padRow(`Bill: ${invoiceNo}`, `${date} ${time}`, colWidth));
  addLine(`Customer: ${customerName}`);
  addLine(`Payment:  ${paymentMode.toUpperCase()}`);
  addLine(doubleDivider);

  // 4. Items Table Header
  if (colWidth >= 48) {
    addLine(padRow('ITEM NAME', 'QTY   RATE   TOTAL', colWidth));
  } else {
    addLine(padRow('ITEM', 'QTY  TOTAL', colWidth));
  }
  addLine(divider);

  // 5. Items Lines
  billItems.forEach((it, idx) => {
    const name = `${idx + 1}. ${it.item_name || 'Item'}`;
    const qty = `${it.quantity}x`;
    const total = `₹${Number(it.item_total || 0).toFixed(2)}`;

    if (colWidth >= 48) {
      const rate = `₹${Number(it.unit_price || 0).toFixed(0)}`;
      const rightCol = `${qty.padStart(3)} ${rate.padStart(6)} ${total.padStart(8)}`;
      if (name.length + rightCol.length >= colWidth) {
        addLine(name);
        addLine(' '.repeat(colWidth - rightCol.length) + rightCol);
      } else {
        addLine(padRow(name, rightCol, colWidth));
      }
    } else {
      const rightCol = `${qty} ${total}`;
      if (name.length + rightCol.length >= colWidth) {
        addLine(name.slice(0, colWidth - 1));
        addLine(' '.repeat(colWidth - rightCol.length) + rightCol);
      } else {
        addLine(padRow(name, rightCol, colWidth));
      }
    }
  });

  // 6. Totals
  addLine(divider);
  addBytes(CMD.ALIGN_LEFT);
  addLine(padRow('Subtotal:', `₹${Number(subtotal).toFixed(2)}`, colWidth));

  addBytes(CMD.BOLD_ON);
  addBytes(CMD.DOUBLE_WIDTH);
  addLine(padRow('TOTAL:', `₹${Number(grandTotal).toFixed(2)}`, Math.floor(colWidth / 2)));
  addBytes(CMD.NORMAL_SIZE);
  addBytes(CMD.BOLD_OFF);

  // 7. Udhaar Khata Details
  if (paymentMode === 'udhaar') {
    addLine(divider);
    const newBal = Number(customerBalance) + Number(grandTotal);
    addLine(padRow('Previous Udhaar:', `₹${Number(customerBalance).toFixed(2)}`, colWidth));
    addBytes(CMD.BOLD_ON);
    addLine(padRow('Total Udhaar Baaki:', `₹${Number(newBal).toFixed(2)}`, colWidth));
    addBytes(CMD.BOLD_OFF);
  }

  // 8. Footer & Barcode/QR Notice
  addLine(doubleDivider);
  addBytes(CMD.ALIGN_CENTER);
  addLine('Thank you! Visit again.');
  addLine('Powered by KiranaSync POS');
  addBytes(CMD.FEED_LINE);
  addBytes(CMD.FEED_LINE);
  addBytes(CMD.FEED_LINE);

  // 9. Cut Paper
  addBytes(CMD.FEED_AND_CUT);

  // Concatenate all chunks into a single Uint8Array
  const totalLength = byteArrays.reduce((acc, curr) => acc + curr.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const arr of byteArrays) {
    result.set(arr, offset);
    offset += arr.length;
  }

  return result;
}

/**
 * Print directly to a Bluetooth ESC/POS thermal printer via Web Bluetooth API
 */
export async function printDirectThermal(billData, options = {}) {
  if (!isBluetoothSupported()) {
    throw new Error(
      'Web Bluetooth is not supported in this browser. Please use Chrome/Edge on Desktop/Android or use the standard Print button.'
    );
  }

  let device;
  try {
    device = await navigator.bluetooth.requestDevice({
      filters: [
        { services: ['000018f0-0000-1000-8000-00805f9b34fb'] },
        { services: ['49535343-fe7d-4ae5-8fa9-9fafd205e455'] },
        { services: ['e7810a71-73ae-499d-8c15-faa9aef0c3f2'] },
      ],
      optionalServices: PRINTER_SERVICES,
    });
  } catch (err) {
    // If specific filters fail or user cancelled, try acceptAllDevices fallback
    if (err.name === 'NotFoundError') {
      throw new Error('No Bluetooth printer selected.', { cause: err });
    }
    try {
      device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: PRINTER_SERVICES,
      });
    } catch (innerErr) {
      throw new Error(innerErr.message || 'Bluetooth printer connection cancelled.', { cause: innerErr });
    }
  }

  if (!device || !device.gatt) {
    throw new Error('Could not access Bluetooth GATT interface.');
  }

  const server = await device.gatt.connect();

  // Search for an active printer service and writable characteristic
  let targetCharacteristic = null;

  for (const sUuid of PRINTER_SERVICES) {
    try {
      const service = await server.getPrimaryService(sUuid);
      const characteristics = await service.getCharacteristics();
      for (const char of characteristics) {
        if (char.properties.write || char.properties.writeWithoutResponse) {
          targetCharacteristic = char;
          break;
        }
      }
      if (targetCharacteristic) break;
    } catch {
      // Service not supported on this device, continue
    }
  }

  if (!targetCharacteristic) {
    // Fallback: search all primary services
    try {
      const services = await server.getPrimaryServices();
      for (const service of services) {
        const characteristics = await service.getCharacteristics();
        for (const char of characteristics) {
          if (char.properties.write || char.properties.writeWithoutResponse) {
            targetCharacteristic = char;
            break;
          }
        }
        if (targetCharacteristic) break;
      }
    } catch (err) {
      console.warn('GATT search error:', err);
    }
  }

  if (!targetCharacteristic) {
    device.gatt.disconnect();
    throw new Error('Connected to device, but no writable printer characteristic found.');
  }

  // Generate binary payload
  const rawBytes = buildReceiptEscPos(billData, options);

  // Send bytes in MTU chunks (standard BLE chunk size is 100 bytes)
  const chunkSize = 100;
  for (let i = 0; i < rawBytes.length; i += chunkSize) {
    const chunk = rawBytes.slice(i, i + chunkSize);
    if (targetCharacteristic.properties.writeWithoutResponse) {
      await targetCharacteristic.writeValueWithoutResponse(chunk);
    } else {
      await targetCharacteristic.writeValue(chunk);
    }
    // Small delay to prevent printer buffer overrun
    await new Promise((res) => setTimeout(res, 20));
  }

  // Disconnect after slight delay to ensure buffer drained
  setTimeout(() => {
    try {
      device.gatt.disconnect();
    } catch {
      // Ignore disconnect errors
    }
  }, 1000);

  return { success: true, deviceName: device.name || 'Bluetooth Printer' };
}
