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
    voiceLanguage: "Voice command language",
    displayLanguage: "Dashboard language",
    autoDetect: "Auto-detect (tries all 10)",
    autoDetectHint: "Auto-detect sends up to 10 Gnani transcription requests for each command.",
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
    similarProductNames: "Similar-sounding product name suggestions (verify before selecting):",
    searchSuggestedName: "Search this name",
    suggestionSearchError: "Could not search for similar names. Edit the product name and try again.",
    purchaseTotal: "Purchase total",
    sourceLabel: "Web sources",
    confirmAddBtn: "Confirm & Add to Inventory",
    cancelBtn: "Cancel",
    selectProductTitle: "Choose the exact product",
    selectProductDesc: "More than one version matches this command. Select the correct MRP/size before inventory is changed.",
    availableStock: "In stock",
    confirmProduct: "Confirm product",
    reviewTitle: "Confirm voice transaction",
    reviewDescription: "Check the details before anything changes. You can edit the action, item or customer, and amount.",
    transactionAction: "Transaction",
    transactionEntity: "Item or customer",
    transactionQuantity: "Quantity / amount",
    transactionSell: "Sale",
    transactionRestock: "Restock",
    transactionCredit: "Customer credit",
    transactionInventoryAdd: "Add new inventory item",
    transactionCreditAdd: "Add customer credit",
    transactionPrice: "Price per item (₹)",
    estimatedTotal: "Estimated transaction total",
    readDetails: "Read details aloud",
    confirmTransaction: "Confirm transaction",
    invalidTransaction: "Enter a name and a positive whole-number quantity or amount.",
    ttsError: "Could not generate the spoken confirmation. Please try again.",
    reviewSpeechSale: (quantity, entity, price) => `Please confirm sale: ${quantity} of ${entity}${price ? `. Estimated total: rupees ${Number(price) * Number(quantity)}` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `Please confirm restock: ${quantity} of ${entity}${price ? `. Estimated restock cost: rupees ${Number(price) * Number(quantity)}` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `Please confirm customer credit: rupees ${quantity} for ${entity}.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `Please confirm adding ${quantity} ${entity} to inventory at rupees ${price} each. Total: rupees ${Number(price) * Number(quantity)}.`,
    reviewSpeechCreditAdd: (quantity, entity) => `Please confirm adding rupees ${quantity} credit for ${entity}.`,
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
    voiceLanguage: "वॉयस कमांड की भाषा",
    displayLanguage: "डैशबोर्ड की भाषा",
    autoDetect: "स्वचालित पहचान (10 भाषाओं में जांच)",
    autoDetectHint: "स्वचालित पहचान हर कमांड के लिए Gnani को अधिकतम 10 ट्रांसक्रिप्शन अनुरोध भेजती है।",
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
    confirmProduct: "उत्पाद की पुष्टि करें",
    reviewTitle: "वॉयस लेन-देन की पुष्टि करें",
    reviewDescription: "बदलाव करने से पहले विवरण जांचें। आप कार्रवाई, आइटम या ग्राहक और मात्रा बदल सकते हैं।",
    transactionAction: "लेन-देन",
    transactionEntity: "आइटम या ग्राहक",
    transactionQuantity: "मात्रा / राशि",
    transactionSell: "बिक्री",
    transactionRestock: "स्टॉक जोड़ें",
    transactionCredit: "ग्राहक उधार",
    transactionInventoryAdd: "नया आइटम जोड़ें",
    transactionCreditAdd: "ग्राहक का उधार जोड़ें",
    transactionPrice: "प्रति आइटम कीमत (₹)",
    estimatedTotal: "अनुमानित कुल राशि",
    readDetails: "विवरण बोलकर सुनें",
    confirmTransaction: "लेन-देन की पुष्टि करें",
    invalidTransaction: "नाम और सकारात्मक पूर्ण संख्या की मात्रा या राशि दर्ज करें।",
    ttsError: "बोली गई पुष्टि तैयार नहीं हो सकी। कृपया फिर से कोशिश करें।",
    reviewSpeechSale: (quantity, entity, price) => `बिक्री की पुष्टि करें: ${entity}, मात्रा ${quantity}${price ? `. अनुमानित कुल ${Number(price) * Number(quantity)} रुपये` : ''}।`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity} का स्टॉक जोड़ने की पुष्टि करें: मात्रा ${quantity}${price ? `. अनुमानित लागत ${Number(price) * Number(quantity)} रुपये` : ''}।`,
    reviewSpeechCredit: (quantity, entity) => `${entity} के खाते में ${quantity} रुपये उधार जोड़ने की पुष्टि करें।`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `प्रति आइटम ${price} रुपये की कीमत पर ${quantity} ${entity} इन्वेंटरी में जोड़ने की पुष्टि करें। कुल ${Number(price) * Number(quantity)} रुपये।`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity} के लिए ${quantity} रुपये उधार जोड़ने की पुष्टि करें।`,
  },
  bn: {
    title: "কিরানাসিঙ্ক লাইভ ড্যাশবোর্ড", invTitle: "📦 লাইভ ইনভেন্টরি", addBtn: "+ যোগ করুন",
    editBtn: "সম্পাদনা", saveBtn: "সংরক্ষণ", itemPlace: "ব্র্যান্ড / পণ্যের নাম", qtyPlace: "স্টকের পরিমাণ",
    pricePlace: "দাম (₹)", saveItem: "পণ্য সংরক্ষণ", thItem: "পণ্যের নাম", thStock: "স্টক", thPrice: "দাম",
    thAction: "কাজ", credTitle: "📒 গ্রাহকের বাকি", ledgerTitle: "📜 লেনদেনের খতিয়ান",
    ledgerEmpty: "এখনও কোনো লেনদেন নেই।", ledgerDate: "তারিখ ও সময়", ledgerType: "ধরন",
    ledgerEntity: "পণ্য / গ্রাহক", ledgerQuantity: "পরিমাণ", ledgerAmount: "টাকার পরিমাণ",
    ledgerDetails: "বিবরণ", custPlace: "গ্রাহকের নাম", balPlace: "বাকি (₹)", saveCust: "গ্রাহক সংরক্ষণ",
    thCust: "গ্রাহক", thBal: "বাকি", voiceTitle: "কিরানাসিঙ্ক ভয়েস",
    defaultListening: "ভয়েস কমান্ডের জন্য শুনছি...", processing: "Gnani AI দিয়ে প্রক্রিয়াকরণ হচ্ছে...",
    voiceLanguage: "ভয়েস কমান্ডের ভাষা", autoDetect: "স্বয়ংক্রিয় শনাক্তকরণ (১০টি ভাষা)",
    displayLanguage: "ড্যাশবোর্ডের ভাষা",
    micError: "মাইক্রোফোন ব্যবহারের অনুমতি দিন।", connError: "ব্যাকএন্ডে সংযোগ করা যায়নি।",
    reviewTitle: "ভয়েস লেনদেন নিশ্চিত করুন", reviewDescription: "পরিবর্তনের আগে বিবরণ যাচাই করুন।",
    transactionAction: "লেনদেন", transactionEntity: "পণ্য বা গ্রাহক", transactionQuantity: "পরিমাণ / টাকা",
    transactionSell: "বিক্রি", transactionRestock: "স্টক যোগ", transactionCredit: "গ্রাহকের বাকি",
    transactionPrice: "প্রতি পণ্যের দাম (₹)", estimatedTotal: "আনুমানিক মোট",
    readDetails: "বিবরণ শুনুন", confirmTransaction: "লেনদেন নিশ্চিত করুন", cancelBtn: "বাতিল",
    confirmAddBtn: "নিশ্চিত করে ইনভেন্টরিতে যোগ করুন", ttsError: "ভয়েস নিশ্চিতকরণ তৈরি করা যায়নি।",
    reviewSpeechSale: (quantity, entity, price) => `${entity}-এর ${quantity}টি বিক্রি নিশ্চিত করুন${price ? `. আনুমানিক মোট ${Number(price) * Number(quantity)} টাকা` : ''}।`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}-এর ${quantity}টি স্টক যোগ নিশ্চিত করুন${price ? `. আনুমানিক খরচ ${Number(price) * Number(quantity)} টাকা` : ''}।`,
    reviewSpeechCredit: (quantity, entity) => `${entity}-এর জন্য ${quantity} টাকা গ্রাহক বাকি নিশ্চিত করুন।`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `${quantity}টি ${entity} ইনভেন্টরিতে যোগ নিশ্চিত করুন। প্রতিটির দাম ${price} টাকা, মোট ${Number(price) * Number(quantity)} টাকা।`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity}-এর নামে ${quantity} টাকা বাকি যোগ নিশ্চিত করুন।`,
  },
  gu: {
    title: "કિરાણાસિંક લાઇવ ડેશબોર્ડ", invTitle: "📦 લાઇવ ઇન્વેન્ટરી", addBtn: "+ ઉમેરો",
    editBtn: "ફેરફાર", saveBtn: "સાચવો", itemPlace: "બ્રાન્ડ / વસ્તુનું નામ", qtyPlace: "સ્ટોક જથ્થો",
    pricePlace: "કિંમત (₹)", saveItem: "વસ્તુ સાચવો", thItem: "વસ્તુનું નામ", thStock: "સ્ટોક",
    thPrice: "કિંમત", thAction: "ક્રિયા", credTitle: "📒 ગ્રાહક ઉધાર", ledgerTitle: "📜 વ્યવહાર નોંધ",
    ledgerEmpty: "હજુ કોઈ વ્યવહાર નથી.", ledgerDate: "તારીખ અને સમય", ledgerType: "પ્રકાર",
    ledgerEntity: "વસ્તુ / ગ્રાહક", ledgerQuantity: "જથ્થો", ledgerAmount: "રકમ",
    ledgerDetails: "વિગતો", custPlace: "ગ્રાહકનું નામ", balPlace: "બાકી રકમ (₹)", saveCust: "ગ્રાહક સાચવો",
    thCust: "ગ્રાહક", thBal: "બાકી", voiceTitle: "કિરાણાસિંક અવાજ",
    defaultListening: "વોઇસ કમાન્ડ સાંભળી રહ્યું છે...", processing: "Gnani AI દ્વારા પ્રક્રિયા થઈ રહી છે...",
    voiceLanguage: "વોઇસ કમાન્ડની ભાષા", autoDetect: "સ્વતઃ શોધ (10 ભાષાઓ)",
    displayLanguage: "ડેશબોર્ડની ભાષા",
    micError: "માઇક્રોફોનની પરવાનગી આપો.", connError: "બૅકએન્ડ સાથે જોડાણ નિષ્ફળ.",
    reviewTitle: "વોઇસ વ્યવહારની પુષ્ટિ કરો", reviewDescription: "ફેરફાર પહેલાં વિગતો તપાસો.",
    transactionAction: "વ્યવહાર", transactionEntity: "વસ્તુ અથવા ગ્રાહક", transactionQuantity: "જથ્થો / રકમ",
    transactionSell: "વેચાણ", transactionRestock: "સ્ટોક ઉમેરો", transactionCredit: "ગ્રાહક ઉધાર",
    transactionPrice: "એક વસ્તુની કિંમત (₹)", estimatedTotal: "અંદાજિત કુલ",
    readDetails: "વિગતો અવાજમાં સાંભળો", confirmTransaction: "વ્યવહારની પુષ્ટિ કરો", cancelBtn: "રદ કરો",
    confirmAddBtn: "પુષ્ટિ કરીને ઇન્વેન્ટરીમાં ઉમેરો", ttsError: "અવાજની પુષ્ટિ બનાવી શકાયી નથી.",
    reviewSpeechSale: (quantity, entity, price) => `${entity}ના ${quantity} વેચાણની પુષ્ટિ કરો${price ? `. અંદાજિત કુલ ${Number(price) * Number(quantity)} રૂપિયા` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}ના ${quantity} સ્ટોક ઉમેરવાની પુષ્ટિ કરો${price ? `. અંદાજિત ખર્ચ ${Number(price) * Number(quantity)} રૂપિયા` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity} માટે ${quantity} રૂપિયાનું ગ્રાહક ઉધાર ખાતરી કરો.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `${price} રૂપિયા પ્રતિ વસ્તુના ભાવે ${quantity} ${entity} ઇન્વેન્ટરીમાં ઉમેરવાની પુષ્ટિ કરો. કુલ ${Number(price) * Number(quantity)} રૂપિયા.`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity} માટે ${quantity} રૂપિયા ઉધાર ઉમેરવાની પુષ્ટિ કરો.`,
  },
  kn: {
    title: "ಕಿರಾಣಾಸಿಂಕ್ ಲೈವ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", invTitle: "📦 ಲೈವ್ ದಾಸ್ತಾನು", addBtn: "+ ಸೇರಿಸಿ",
    editBtn: "ತಿದ್ದು", saveBtn: "ಉಳಿಸಿ", itemPlace: "ಬ್ರ್ಯಾಂಡ್ / ವಸ್ತುವಿನ ಹೆಸರು", qtyPlace: "ದಾಸ್ತಾನು ಪ್ರಮಾಣ",
    pricePlace: "ಬೆಲೆ (₹)", saveItem: "ವಸ್ತು ಉಳಿಸಿ", thItem: "ವಸ್ತುವಿನ ಹೆಸರು", thStock: "ದಾಸ್ತಾನು",
    thPrice: "ಬೆಲೆ", thAction: "ಕ್ರಿಯೆ", credTitle: "📒 ಗ್ರಾಹಕರ ಸಾಲ", ledgerTitle: "📜 ವಹಿವಾಟು ಪಟ್ಟಿ",
    ledgerEmpty: "ಇನ್ನೂ ಯಾವುದೇ ವಹಿವಾಟುಗಳಿಲ್ಲ.", ledgerDate: "ದಿನಾಂಕ ಮತ್ತು ಸಮಯ", ledgerType: "ಪ್ರಕಾರ",
    ledgerEntity: "ವಸ್ತು / ಗ್ರಾಹಕ", ledgerQuantity: "ಪ್ರಮಾಣ", ledgerAmount: "ಮೊತ್ತ", ledgerDetails: "ವಿವರಗಳು",
    custPlace: "ಗ್ರಾಹಕರ ಹೆಸರು", balPlace: "ಬಾಕಿ ಮೊತ್ತ (₹)", saveCust: "ಗ್ರಾಹಕರನ್ನು ಉಳಿಸಿ",
    thCust: "ಗ್ರಾಹಕ", thBal: "ಬಾಕಿ", voiceTitle: "ಕಿರಾಣಾಸಿಂಕ್ ಧ್ವನಿ",
    defaultListening: "ಧ್ವನಿ ಆಜ್ಞೆಗಾಗಿ ಕೇಳುತ್ತಿದೆ...", processing: "Gnani AI ಮೂಲಕ ಪ್ರಕ್ರಿಯೆ ನಡೆಯುತ್ತಿದೆ...",
    voiceLanguage: "ಧ್ವನಿ ಆಜ್ಞೆಯ ಭಾಷೆ", autoDetect: "ಸ್ವಯಂ ಪತ್ತೆ (10 ಭಾಷೆಗಳು)",
    displayLanguage: "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ ಭಾಷೆ",
    micError: "ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿಸಿ.", connError: "ಬ್ಯಾಕೆಂಡ್ ಸಂಪರ್ಕ ವಿಫಲವಾಗಿದೆ.",
    reviewTitle: "ಧ್ವನಿ ವಹಿವಾಟನ್ನು ದೃಢೀಕರಿಸಿ", reviewDescription: "ಬದಲಾವಣೆಗೂ ಮೊದಲು ವಿವರಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.",
    transactionAction: "ವಹಿವಾಟು", transactionEntity: "ವಸ್ತು ಅಥವಾ ಗ್ರಾಹಕ", transactionQuantity: "ಪ್ರಮಾಣ / ಮೊತ್ತ",
    transactionSell: "ಮಾರಾಟ", transactionRestock: "ದಾಸ್ತಾನು ಸೇರಿಸಿ", transactionCredit: "ಗ್ರಾಹಕರ ಸಾಲ",
    transactionPrice: "ಪ್ರತಿ ವಸ್ತುವಿನ ಬೆಲೆ (₹)", estimatedTotal: "ಅಂದಾಜು ಒಟ್ಟು",
    readDetails: "ವಿವರಗಳನ್ನು ಧ್ವನಿಯಲ್ಲಿ ಕೇಳಿ", confirmTransaction: "ವಹಿವಾಟನ್ನು ದೃಢೀಕರಿಸಿ", cancelBtn: "ರದ್ದುಮಾಡಿ",
    confirmAddBtn: "ದೃಢೀಕರಿಸಿ ದಾಸ್ತಾನಿಗೆ ಸೇರಿಸಿ", ttsError: "ಧ್ವನಿ ದೃಢೀಕರಣವನ್ನು ರಚಿಸಲಾಗಲಿಲ್ಲ.",
    reviewSpeechSale: (quantity, entity, price) => `${entity}ಯ ${quantity} ಮಾರಾಟವನ್ನು ದೃಢೀಕರಿಸಿ${price ? `. ಅಂದಾಜು ಒಟ್ಟು ${Number(price) * Number(quantity)} ರೂಪಾಯಿ` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}ಯ ${quantity} ದಾಸ್ತಾನು ಸೇರಿಸುವುದನ್ನು ದೃಢೀಕರಿಸಿ${price ? `. ಅಂದಾಜು ವೆಚ್ಚ ${Number(price) * Number(quantity)} ರೂಪಾಯಿ` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity}ಗೆ ${quantity} ರೂಪಾಯಿ ಗ್ರಾಹಕರ ಸಾಲವನ್ನು ದೃಢೀಕರಿಸಿ.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `ಪ್ರತಿ ವಸ್ತುವಿಗೆ ${price} ರೂಪಾಯಿಯಂತೆ ${quantity} ${entity} ಸೇರಿಸುವುದನ್ನು ದೃಢೀಕರಿಸಿ. ಒಟ್ಟು ${Number(price) * Number(quantity)} ರೂಪಾಯಿ.`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity}ಗೆ ${quantity} ರೂಪಾಯಿ ಸಾಲ ಸೇರಿಸುವುದನ್ನು ದೃಢೀಕರಿಸಿ.`,
  },
  ml: {
    title: "കിരാണാസിങ്ക് ലൈവ് ഡാഷ്ബോർഡ്", invTitle: "📦 ലൈവ് ഇൻവെന്ററി", addBtn: "+ ചേർക്കുക",
    editBtn: "തിരുത്തുക", saveBtn: "സേവ് ചെയ്യുക", itemPlace: "ബ്രാൻഡ് / സാധനത്തിന്റെ പേര്",
    qtyPlace: "സ്റ്റോക്ക് അളവ്", pricePlace: "വില (₹)", saveItem: "സാധനം സേവ് ചെയ്യുക",
    thItem: "സാധനത്തിന്റെ പേര്", thStock: "സ്റ്റോക്ക്", thPrice: "വില", thAction: "പ്രവർത്തനം",
    credTitle: "📒 ഉപഭോക്തൃ കുടിശ്ശിക", ledgerTitle: "📜 ഇടപാട് രേഖ",
    ledgerEmpty: "ഇതുവരെ ഇടപാടുകളില്ല.", ledgerDate: "തീയതിയും സമയവും", ledgerType: "തരം",
    ledgerEntity: "സാധനം / ഉപഭോക്താവ്", ledgerQuantity: "അളവ്", ledgerAmount: "തുക",
    ledgerDetails: "വിശദാംശങ്ങൾ", custPlace: "ഉപഭോക്താവിന്റെ പേര്", balPlace: "ബാക്കി തുക (₹)",
    saveCust: "ഉപഭോക്താവിനെ സേവ് ചെയ്യുക", thCust: "ഉപഭോക്താവ്", thBal: "ബാക്കി",
    voiceTitle: "കിരാണാസിങ്ക് വോയ്സ്", defaultListening: "വോയ്സ് കമാൻഡിനായി കേൾക്കുന്നു...",
    processing: "Gnani AI ഉപയോഗിച്ച് പ്രോസസ്സ് ചെയ്യുന്നു...", voiceLanguage: "വോയ്സ് കമാൻഡിന്റെ ഭാഷ",
    autoDetect: "സ്വയം കണ്ടെത്തുക (10 ഭാഷകൾ)", micError: "മൈക്രോഫോൺ അനുമതി നൽകുക.",
    displayLanguage: "ഡാഷ്ബോർഡിന്റെ ഭാഷ",
    connError: "ബാക്കെൻഡുമായി ബന്ധപ്പെടാനായില്ല.", reviewTitle: "വോയ്സ് ഇടപാട് സ്ഥിരീകരിക്കുക",
    reviewDescription: "മാറ്റങ്ങൾ വരുത്തുന്നതിന് മുമ്പ് വിവരങ്ങൾ പരിശോധിക്കുക.",
    transactionAction: "ഇടപാട്", transactionEntity: "സാധനം അല്ലെങ്കിൽ ഉപഭോക്താവ്",
    transactionQuantity: "അളവ് / തുക", transactionSell: "വിൽപ്പന", transactionRestock: "സ്റ്റോക്ക് ചേർക്കുക",
    transactionCredit: "ഉപഭോക്തൃ കുടിശ്ശിക", transactionPrice: "ഓരോ സാധനത്തിന്റെയും വില (₹)",
    estimatedTotal: "ഏകദേശ ആകെ തുക", readDetails: "വിശദാംശങ്ങൾ ശബ്ദത്തിൽ കേൾക്കുക",
    confirmTransaction: "ഇടപാട് സ്ഥിരീകരിക്കുക", cancelBtn: "റദ്ദാക്കുക",
    confirmAddBtn: "സ്ഥിരീകരിച്ച് ഇൻവെന്ററിയിൽ ചേർക്കുക", ttsError: "ശബ്ദ സ്ഥിരീകരണം സൃഷ്ടിക്കാനായില്ല.",
    reviewSpeechSale: (quantity, entity, price) => `${entity}-ന്റെ ${quantity} വിൽപ്പന സ്ഥിരീകരിക്കുക${price ? `. ഏകദേശ മൊത്തം ${Number(price) * Number(quantity)} രൂപ` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}-ന്റെ ${quantity} സ്റ്റോക്ക് ചേർക്കൽ സ്ഥിരീകരിക്കുക${price ? `. ഏകദേശ ചെലവ് ${Number(price) * Number(quantity)} രൂപ` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity}-ന് ${quantity} രൂപ ഉപഭോക്തൃ കുടിശ്ശിക ചേർക്കുന്നത് സ്ഥിരീകരിക്കുക.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `ഒന്നിന് ${price} രൂപ നിരക്കിൽ ${quantity} ${entity} ഇൻവെന്ററിയിൽ ചേർക്കുന്നത് സ്ഥിരീകരിക്കുക. ആകെ ${Number(price) * Number(quantity)} രൂപ.`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity}-ന് ${quantity} രൂപ കുടിശ്ശിക ചേർക്കുന്നത് സ്ഥിരീകരിക്കുക.`,
  },
  mr: {
    title: "किराणासिंक लाइव्ह डॅशबोर्ड", invTitle: "📦 लाइव्ह इन्व्हेंटरी", addBtn: "+ जोडा",
    editBtn: "संपादित करा", saveBtn: "जतन करा", itemPlace: "ब्रँड / वस्तूचे नाव", qtyPlace: "साठ्याचे प्रमाण",
    pricePlace: "किंमत (₹)", saveItem: "वस्तू जतन करा", thItem: "वस्तूचे नाव", thStock: "साठा",
    thPrice: "किंमत", thAction: "कृती", credTitle: "📒 ग्राहक उधार", ledgerTitle: "📜 व्यवहार नोंद",
    ledgerEmpty: "अद्याप कोणतेही व्यवहार नाहीत.", ledgerDate: "दिनांक आणि वेळ", ledgerType: "प्रकार",
    ledgerEntity: "वस्तू / ग्राहक", ledgerQuantity: "प्रमाण", ledgerAmount: "रक्कम", ledgerDetails: "तपशील",
    custPlace: "ग्राहकाचे नाव", balPlace: "बाकी रक्कम (₹)", saveCust: "ग्राहक जतन करा",
    thCust: "ग्राहक", thBal: "बाकी", voiceTitle: "किराणासिंक व्हॉइस",
    defaultListening: "व्हॉइस कमांड ऐकत आहे...", processing: "Gnani AI द्वारे प्रक्रिया सुरू आहे...",
    voiceLanguage: "व्हॉइस कमांडची भाषा", autoDetect: "स्वयंचलित शोध (10 भाषा)",
    displayLanguage: "डॅशबोर्डची भाषा",
    micError: "मायक्रोफोनची परवानगी द्या.", connError: "बॅकएंडशी जोडणी अयशस्वी.",
    reviewTitle: "व्हॉइस व्यवहाराची पुष्टी करा", reviewDescription: "बदल करण्यापूर्वी तपशील तपासा.",
    transactionAction: "व्यवहार", transactionEntity: "वस्तू किंवा ग्राहक", transactionQuantity: "प्रमाण / रक्कम",
    transactionSell: "विक्री", transactionRestock: "साठा जोडा", transactionCredit: "ग्राहक उधार",
    transactionPrice: "प्रति वस्तू किंमत (₹)", estimatedTotal: "अंदाजे एकूण",
    readDetails: "तपशील आवाजात ऐका", confirmTransaction: "व्यवहाराची पुष्टी करा", cancelBtn: "रद्द करा",
    confirmAddBtn: "पुष्टी करून इन्व्हेंटरीमध्ये जोडा", ttsError: "आवाजातील पुष्टी तयार करता आली नाही.",
    reviewSpeechSale: (quantity, entity, price) => `${entity}ची ${quantity} विक्री निश्चित करा${price ? `. अंदाजे एकूण ${Number(price) * Number(quantity)} रुपये` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}चा ${quantity} साठा जोडणे निश्चित करा${price ? `. अंदाजे खर्च ${Number(price) * Number(quantity)} रुपये` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity}साठी ${quantity} रुपये ग्राहक उधार निश्चित करा.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `प्रति वस्तू ${price} रुपये दराने ${quantity} ${entity} इन्व्हेंटरीमध्ये जोडणे निश्चित करा. एकूण ${Number(price) * Number(quantity)} रुपये.`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity}साठी ${quantity} रुपये उधार जोडणे निश्चित करा.`,
  },
  pa: {
    title: "ਕਿਰਾਨਾਸਿੰਕ ਲਾਈਵ ਡੈਸ਼ਬੋਰਡ", invTitle: "📦 ਲਾਈਵ ਸਟਾਕ", addBtn: "+ ਜੋੜੋ",
    editBtn: "ਸੋਧੋ", saveBtn: "ਸੰਭਾਲੋ", itemPlace: "ਬ੍ਰਾਂਡ / ਚੀਜ਼ ਦਾ ਨਾਮ", qtyPlace: "ਸਟਾਕ ਦੀ ਮਾਤਰਾ",
    pricePlace: "ਕੀਮਤ (₹)", saveItem: "ਚੀਜ਼ ਸੰਭਾਲੋ", thItem: "ਚੀਜ਼ ਦਾ ਨਾਮ", thStock: "ਸਟਾਕ",
    thPrice: "ਕੀਮਤ", thAction: "ਕਾਰਵਾਈ", credTitle: "📒 ਗਾਹਕ ਉਧਾਰ", ledgerTitle: "📜 ਲੈਣ-ਦੇਣ ਦਾ ਰਿਕਾਰਡ",
    ledgerEmpty: "ਹਾਲੇ ਕੋਈ ਲੈਣ-ਦੇਣ ਨਹੀਂ।", ledgerDate: "ਤਾਰੀਖ ਅਤੇ ਸਮਾਂ", ledgerType: "ਕਿਸਮ",
    ledgerEntity: "ਚੀਜ਼ / ਗਾਹਕ", ledgerQuantity: "ਮਾਤਰਾ", ledgerAmount: "ਰਕਮ",
    ledgerDetails: "ਵੇਰਵਾ", custPlace: "ਗਾਹਕ ਦਾ ਨਾਮ", balPlace: "ਬਕਾਇਆ (₹)", saveCust: "ਗਾਹਕ ਸੰਭਾਲੋ",
    thCust: "ਗਾਹਕ", thBal: "ਬਕਾਇਆ", voiceTitle: "ਕਿਰਾਨਾਸਿੰਕ ਆਵਾਜ਼",
    defaultListening: "ਵੌਇਸ ਕਮਾਂਡ ਸੁਣ ਰਿਹਾ ਹੈ...", processing: "Gnani AI ਨਾਲ ਕਾਰਵਾਈ ਹੋ ਰਹੀ ਹੈ...",
    voiceLanguage: "ਵੌਇਸ ਕਮਾਂਡ ਦੀ ਭਾਸ਼ਾ", autoDetect: "ਆਪਣੇ ਆਪ ਪਛਾਣੋ (10 ਭਾਸ਼ਾਵਾਂ)",
    displayLanguage: "ਡੈਸ਼ਬੋਰਡ ਦੀ ਭਾਸ਼ਾ",
    micError: "ਮਾਈਕ੍ਰੋਫ਼ੋਨ ਦੀ ਇਜਾਜ਼ਤ ਦਿਓ।", connError: "ਬੈਕਐਂਡ ਨਾਲ ਕਨੈਕਟ ਨਹੀਂ ਹੋਇਆ।",
    reviewTitle: "ਵੌਇਸ ਲੈਣ-ਦੇਣ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ", reviewDescription: "ਬਦਲਾਅ ਤੋਂ ਪਹਿਲਾਂ ਵੇਰਵੇ ਜਾਂਚੋ।",
    transactionAction: "ਲੈਣ-ਦੇਣ", transactionEntity: "ਚੀਜ਼ ਜਾਂ ਗਾਹਕ", transactionQuantity: "ਮਾਤਰਾ / ਰਕਮ",
    transactionSell: "ਵਿਕਰੀ", transactionRestock: "ਸਟਾਕ ਜੋੜੋ", transactionCredit: "ਗਾਹਕ ਉਧਾਰ",
    transactionPrice: "ਹਰ ਚੀਜ਼ ਦੀ ਕੀਮਤ (₹)", estimatedTotal: "ਅੰਦਾਜ਼ਨ ਕੁੱਲ",
    readDetails: "ਵੇਰਵੇ ਆਵਾਜ਼ ਵਿੱਚ ਸੁਣੋ", confirmTransaction: "ਲੈਣ-ਦੇਣ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ", cancelBtn: "ਰੱਦ ਕਰੋ",
    confirmAddBtn: "ਪੁਸ਼ਟੀ ਕਰਕੇ ਸਟਾਕ ਵਿੱਚ ਜੋੜੋ", ttsError: "ਆਵਾਜ਼ ਦੀ ਪੁਸ਼ਟੀ ਤਿਆਰ ਨਹੀਂ ਹੋ ਸਕੀ।",
    reviewSpeechSale: (quantity, entity, price) => `${entity} ਦੇ ${quantity} ਵੇਚਣ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ${price ? `. ਅੰਦਾਜ਼ਨ ਕੁੱਲ ${Number(price) * Number(quantity)} ਰੁਪਏ` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity} ਦੇ ${quantity} ਸਟਾਕ ਜੋੜਨ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ${price ? `. ਅੰਦਾਜ਼ਨ ਖਰਚਾ ${Number(price) * Number(quantity)} ਰੁਪਏ` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity} ਲਈ ${quantity} ਰੁਪਏ ਗਾਹਕ ਉਧਾਰ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ।`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `ਹਰ ਚੀਜ਼ ਦੀ ਕੀਮਤ ${price} ਰੁਪਏ ਰੱਖ ਕੇ ${quantity} ${entity} ਸਟਾਕ ਵਿੱਚ ਜੋੜਨ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ। ਕੁੱਲ ${Number(price) * Number(quantity)} ਰੁਪਏ।`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity} ਲਈ ${quantity} ਰੁਪਏ ਉਧਾਰ ਜੋੜਨ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ।`,
  },
  ta: {
    title: "கிரணாசிங்க் நேரலை பலகை", invTitle: "📦 நேரலை சரக்கு", addBtn: "+ சேர்",
    editBtn: "திருத்து", saveBtn: "சேமி", itemPlace: "பிராண்ட் / பொருளின் பெயர்", qtyPlace: "சரக்கு அளவு",
    pricePlace: "விலை (₹)", saveItem: "பொருளைச் சேமி", thItem: "பொருளின் பெயர்", thStock: "சரக்கு",
    thPrice: "விலை", thAction: "செயல்", credTitle: "📒 வாடிக்கையாளர் கடன்",
    ledgerTitle: "📜 பரிவர்த்தனைப் பதிவு", ledgerEmpty: "இதுவரை பரிவர்த்தனைகள் இல்லை.",
    ledgerDate: "தேதி மற்றும் நேரம்", ledgerType: "வகை", ledgerEntity: "பொருள் / வாடிக்கையாளர்",
    ledgerQuantity: "அளவு", ledgerAmount: "தொகை", ledgerDetails: "விவரங்கள்",
    custPlace: "வாடிக்கையாளர் பெயர்", balPlace: "நிலுவைத் தொகை (₹)", saveCust: "வாடிக்கையாளரைச் சேமி",
    thCust: "வாடிக்கையாளர்", thBal: "நிலுவை", voiceTitle: "கிரணாசிங்க் குரல்",
    defaultListening: "குரல் கட்டளைக்காகக் கேட்கிறது...", processing: "Gnani AI மூலம் செயலாக்கப்படுகிறது...",
    voiceLanguage: "குரல் கட்டளை மொழி", autoDetect: "தானாகக் கண்டறி (10 மொழிகள்)",
    displayLanguage: "டாஷ்போர்டு மொழி",
    micError: "மைக்ரோஃபோன் அனுமதி வழங்கவும்.", connError: "பின்தளத்துடன் இணைக்க முடியவில்லை.",
    reviewTitle: "குரல் பரிவர்த்தனையை உறுதிப்படுத்தவும்", reviewDescription: "மாற்றுவதற்கு முன் விவரங்களைச் சரிபார்க்கவும்.",
    transactionAction: "பரிவர்த்தனை", transactionEntity: "பொருள் அல்லது வாடிக்கையாளர்",
    transactionQuantity: "அளவு / தொகை", transactionSell: "விற்பனை", transactionRestock: "சரக்கைச் சேர்",
    transactionCredit: "வாடிக்கையாளர் கடன்", transactionPrice: "ஒரு பொருளின் விலை (₹)",
    estimatedTotal: "மதிப்பிடப்பட்ட மொத்தம்", readDetails: "விவரங்களைச் சத்தமாகக் கேள்",
    confirmTransaction: "பரிவர்த்தனையை உறுதிப்படுத்து", cancelBtn: "ரத்து செய்",
    confirmAddBtn: "உறுதிப்படுத்தி சரக்கில் சேர்", ttsError: "குரல் உறுதிப்படுத்தலை உருவாக்க முடியவில்லை.",
    reviewSpeechSale: (quantity, entity, price) => `${entity}-இன் ${quantity} விற்பனையை உறுதிப்படுத்தவும்${price ? `. மதிப்பிடப்பட்ட மொத்தம் ${Number(price) * Number(quantity)} ரூபாய்` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}-இன் ${quantity} சரக்கு சேர்ப்பை உறுதிப்படுத்தவும்${price ? `. மதிப்பிடப்பட்ட செலவு ${Number(price) * Number(quantity)} ரூபாய்` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity}-க்கு ${quantity} ரூபாய் வாடிக்கையாளர் கடனை உறுதிப்படுத்தவும்.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `ஒவ்வொன்றும் ${price} ரூபாய் விலையில் ${quantity} ${entity} சரக்கில் சேர்ப்பதை உறுதிப்படுத்தவும். மொத்தம் ${Number(price) * Number(quantity)} ரூபாய்.`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity}-க்கு ${quantity} ரூபாய் கடன் சேர்ப்பதை உறுதிப்படுத்தவும்.`,
  },
  te: {
    title: "కిరాణాసింక్ లైవ్ డాష్‌బోర్డ్", invTitle: "📦 లైవ్ ఇన్వెంటరీ", addBtn: "+ జోడించు",
    editBtn: "సవరించు", saveBtn: "సేవ్ చేయి", itemPlace: "బ్రాండ్ / వస్తువు పేరు", qtyPlace: "స్టాక్ పరిమాణం",
    pricePlace: "ధర (₹)", saveItem: "వస్తువును సేవ్ చేయి", thItem: "వస్తువు పేరు", thStock: "స్టాక్",
    thPrice: "ధర", thAction: "చర్య", credTitle: "📒 కస్టమర్ అప్పు", ledgerTitle: "📜 లావాదేవీల జాబితా",
    ledgerEmpty: "ఇంకా లావాదేవీలు లేవు.", ledgerDate: "తేదీ మరియు సమయం", ledgerType: "రకం",
    ledgerEntity: "వస్తువు / కస్టమర్", ledgerQuantity: "పరిమాణం", ledgerAmount: "మొత్తం",
    ledgerDetails: "వివరాలు", custPlace: "కస్టమర్ పేరు", balPlace: "బకాయి (₹)", saveCust: "కస్టమర్‌ను సేవ్ చేయి",
    thCust: "కస్టమర్", thBal: "బకాయి", voiceTitle: "కిరాణాసింక్ వాయిస్",
    defaultListening: "వాయిస్ కమాండ్ కోసం వింటోంది...", processing: "Gnani AIతో ప్రాసెస్ చేస్తోంది...",
    voiceLanguage: "వాయిస్ కమాండ్ భాష", autoDetect: "ఆటో డిటెక్ట్ (10 భాషలు)",
    displayLanguage: "డాష్‌బోర్డ్ భాష",
    micError: "మైక్రోఫోన్ అనుమతి ఇవ్వండి.", connError: "బ్యాకెండ్‌కు కనెక్ట్ కాలేదు.",
    reviewTitle: "వాయిస్ లావాదేవీని నిర్ధారించండి", reviewDescription: "మార్పులకు ముందు వివరాలను తనిఖీ చేయండి.",
    transactionAction: "లావాదేవీ", transactionEntity: "వస్తువు లేదా కస్టమర్", transactionQuantity: "పరిమాణం / మొత్తం",
    transactionSell: "అమ్మకం", transactionRestock: "స్టాక్ జోడించు", transactionCredit: "కస్టమర్ అప్పు",
    transactionPrice: "ఒక్కో వస్తువు ధర (₹)", estimatedTotal: "అంచనా మొత్తం",
    readDetails: "వివరాలను శబ్దంగా వినండి", confirmTransaction: "లావాదేవీని నిర్ధారించండి", cancelBtn: "రద్దు",
    confirmAddBtn: "నిర్ధారించి ఇన్వెంటరీకి జోడించు", ttsError: "వాయిస్ నిర్ధారణను రూపొందించలేకపోయాం.",
    reviewSpeechSale: (quantity, entity, price) => `${entity}కు చెందిన ${quantity} అమ్మకాన్ని నిర్ధారించండి${price ? `. అంచనా మొత్తం ${Number(price) * Number(quantity)} రూపాయలు` : ''}.`,
    reviewSpeechRestock: (quantity, entity, price) => `${entity}కు చెందిన ${quantity} స్టాక్ జోడింపును నిర్ధారించండి${price ? `. అంచనా ఖర్చు ${Number(price) * Number(quantity)} రూపాయలు` : ''}.`,
    reviewSpeechCredit: (quantity, entity) => `${entity} కోసం ${quantity} రూపాయల కస్టమర్ అప్పును నిర్ధారించండి.`,
    reviewSpeechInventoryAdd: (quantity, entity, price) => `ఒక్కో వస్తువుకు ${price} రూపాయల చొప్పున ${quantity} ${entity}ను ఇన్వెంటరీకి జోడించడాన్ని నిర్ధారించండి. మొత్తం ${Number(price) * Number(quantity)} రూపాయలు.`,
    reviewSpeechCreditAdd: (quantity, entity) => `${entity} కోసం ${quantity} రూపాయల అప్పు జోడించడాన్ని నిర్ధారించండి.`,
  }
};

const pendingProductSpeech = {
  bn: (entity, details) => `ইনভেন্টরিতে ${entity} যোগ নিশ্চিত করুন: ${details}।`,
  en: (entity, details) => `Please confirm adding ${entity} to inventory: ${details}.`,
  gu: (entity, details) => `ઇન્વેન્ટરીમાં ${entity} ઉમેરવાની પુષ્ટિ કરો: ${details}.`,
  hi: (entity, details) => `इन्वेंटरी में ${entity} जोड़ने की पुष्टि करें: ${details}।`,
  kn: (entity, details) => `ದಾಸ್ತಾನಿಗೆ ${entity} ಸೇರಿಸುವುದನ್ನು ದೃಢೀಕರಿಸಿ: ${details}.`,
  ml: (entity, details) => `ഇൻവെന്ററിയിൽ ${entity} ചേർക്കുന്നത് സ്ഥിരീകരിക്കുക: ${details}.`,
  mr: (entity, details) => `इन्व्हेंटरीमध्ये ${entity} जोडण्याची पुष्टी करा: ${details}.`,
  pa: (entity, details) => `ਸਟਾਕ ਵਿੱਚ ${entity} ਜੋੜਨ ਦੀ ਪੁਸ਼ਟੀ ਕਰੋ: ${details}।`,
  ta: (entity, details) => `சரக்கில் ${entity} சேர்ப்பதை உறுதிப்படுத்தவும்: ${details}.`,
  te: (entity, details) => `ఇన్వెంటరీకి ${entity} జోడించడాన్ని నిర్ధారించండి: ${details}.`,
};

const productPronunciationCopy = {
  bn: ["উচ্চারণ (ঐচ্ছিক)", "ব্র্যান্ডের নামটি ভুল উচ্চারিত হলে TTS-এর জন্য উচ্চারণ লিখুন। সংরক্ষিত পণ্যের নাম বদলাবে না।", "যেমন: ডাভ"],
  en: ["Pronunciation for voice (optional)", "If Timbre mispronounces the brand, enter a phonetic spelling here. This changes speech only; the saved product name stays the same.", ""],
  gu: ["ઉચ્ચાર (વૈકલ્પિક)", "TTS બ્રાન્ડનું નામ ખોટું બોલે તો અહીં ઉચ્ચાર લખો. સાચવેલા ઉત્પાદનનું નામ બદલાશે નહીં.", "દા.ત.: ડવ"],
  hi: ["उच्चारण (वैकल्पिक)", "अगर Timbre ब्रांड का नाम गलत बोलता है, तो यहां उसका उच्चारण लिखें। सेव किया गया नाम नहीं बदलेगा।", "जैसे: डव"],
  kn: ["ಉಚ್ಚಾರಣೆ (ಐಚ್ಛಿಕ)", "TTS ಬ್ರ್ಯಾಂಡ್ ಹೆಸರನ್ನು ತಪ್ಪಾಗಿ ಉಚ್ಚರಿಸಿದರೆ, ಇಲ್ಲಿ ಉಚ್ಚಾರಣೆಯನ್ನು ಬರೆಯಿರಿ. ಉಳಿಸಿದ ಉತ್ಪನ್ನದ ಹೆಸರು ಬದಲಾಗುವುದಿಲ್ಲ.", "ಉದಾ: ಡವ್"],
  ml: ["ഉച്ചാരണം (ഐച്ഛികം)", "TTS ബ്രാൻഡ് പേര് തെറ്റായി പറയുന്നുവെങ്കിൽ ഇവിടെ ഉച്ചാരണം എഴുതുക. സേവ് ചെയ്യുന്ന ഉൽപ്പന്നത്തിന്റെ പേര് മാറില്ല.", "ഉദാ: ഡവ്"],
  mr: ["उच्चार (ऐच्छिक)", "Timbre ब्रँडचे नाव चुकीचे उच्चारत असल्यास येथे उच्चार लिहा. जतन केलेले नाव बदलणार नाही.", "उदा.: डव्ह"],
  pa: ["ਉਚਾਰਨ (ਵਿਕਲਪਿਕ)", "ਜੇ TTS ਬ੍ਰਾਂਡ ਦਾ ਨਾਮ ਗਲਤ ਬੋਲੇ, ਤਾਂ ਇੱਥੇ ਉਚਾਰਨ ਲਿਖੋ। ਸੰਭਾਲਿਆ ਉਤਪਾਦ ਨਾਮ ਨਹੀਂ ਬਦਲੇਗਾ।", "ਜਿਵੇਂ: ਡਵ"],
  ta: ["உச்சரிப்பு (விருப்பத்தேர்வு)", "TTS பிராண்ட் பெயரைத் தவறாகச் சொன்னால், இங்கே ஒலிப்பை எழுதவும். சேமிக்கப்படும் பெயர் மாறாது.", "எ.கா.: டவ்"],
  te: ["ఉచ్చారణ (ఐచ్ఛికం)", "TTS బ్రాండ్ పేరును తప్పుగా పలికితే, ఇక్కడ ఉచ్చారణను రాయండి. సేవ్ చేసే ఉత్పత్తి పేరు మారదు.", "ఉదా: డవ్"],
};

const voiceLanguages = [
  ["bn-IN", "Bengali"],
  ["en-IN", "English / Hinglish"],
  ["gu-IN", "Gujarati"],
  ["hi-IN", "Hindi"],
  ["kn-IN", "Kannada"],
  ["ml-IN", "Malayalam"],
  ["mr-IN", "Marathi"],
  ["pa-IN", "Punjabi"],
  ["ta-IN", "Tamil"],
  ["te-IN", "Telugu"],
];

const displayLanguages = [
  ["bn", "বাংলা"],
  ["en", "English"],
  ["gu", "ગુજરાતી"],
  ["hi", "हिन्दी"],
  ["kn", "ಕನ್ನಡ"],
  ["ml", "മലയാളം"],
  ["mr", "मराठी"],
  ["pa", "ਪੰਜਾਬੀ"],
  ["ta", "தமிழ்"],
  ["te", "తెలుగు"],
];

export default function App() {
  const [lang, setLang] = useState('en');
  const [speechLanguage, setSpeechLanguage] = useState('auto');
  const t = { ...text.en, ...(text[lang] || {}) };
  const getTtsLanguage = (draft) => {
    if (draft?.LanguageCode && draft.LanguageCode !== 'auto') {
      return draft.LanguageCode;
    }
    return speechLanguage === 'auto' ? 'en-IN' : speechLanguage;
  };
  const getSpeechDictionary = (draft) => text[getTtsLanguage(draft).split('-')[0]] || text.en;
  const productPronunciationText = productPronunciationCopy[lang] || productPronunciationCopy.en;

  const [isActive, setIsActive] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [transcript, setTranscript] = useState(t.defaultListening);
  const [dbAction, setDbAction] = useState(null);
  
  // Confirmation Modal State
  const [pendingDraft, setPendingDraft] = useState(null);
  const [pendingReview, setPendingReview] = useState(null);
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
  const confirmationAudio = useRef(null);
  const speechRequestId = useRef(0);

  const getReviewSpeech = (draft) => {
    const speechText = getSpeechDictionary(draft);
    const speech = {
      sell: speechText.reviewSpeechSale,
      restock: speechText.reviewSpeechRestock,
      credit: speechText.reviewSpeechCredit,
      inventory_add: speechText.reviewSpeechInventoryAdd,
      credit_add: speechText.reviewSpeechCreditAdd,
    }[draft.Intent];
    return speech(draft.Quantity, draft.EntityName, draft.UnitPrice);
  };

  const stopConfirmationAudio = () => {
    speechRequestId.current += 1;
    if (confirmationAudio.current) {
      confirmationAudio.current.pause();
      URL.revokeObjectURL(confirmationAudio.current.src);
      confirmationAudio.current = null;
    }
  };

  const speakText = async (text, language = 'en-IN') => {
    if (!text) return;
    stopConfirmationAudio();
    const requestId = speechRequestId.current;
    let audioUrl;
    setConfirmationError('');
    try {
      const response = await fetch('http://127.0.0.1:5000/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          language,
        }),
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || t.ttsError);
      }
      const audioBlob = await response.blob();
      if (requestId !== speechRequestId.current) return;
      audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      confirmationAudio.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        if (confirmationAudio.current === audio) confirmationAudio.current = null;
      };
      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        if (confirmationAudio.current === audio) confirmationAudio.current = null;
        setConfirmationError(t.ttsError);
      };
      await audio.play();
    } catch (error) {
      if (confirmationAudio.current) {
        confirmationAudio.current.pause();
        confirmationAudio.current = null;
      }
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      if (requestId !== speechRequestId.current) return;
      console.error("Gnani Timbre speech error:", error);
      setConfirmationError(error.message || t.ttsError);
    }
  };

  const speakReview = (draft) => {
    if (!draft) return;
    return speakText(getReviewSpeech(draft), getTtsLanguage(draft));
  };

  const speakPendingProduct = (draft) => {
    if (!draft) return;
    const selected = (draft.PriceOptions || []).filter(
      option => option.Selected && Number(option.Quantity) > 0
    );
    const details = selected.length
      ? selected.map(option => `${option.Quantity} x ₹${option.Price}`).join(', ')
      : `${draft.StockQuantity}`;
    const locale = getTtsLanguage(draft).split('-')[0];
    const spokenName = draft.Pronunciation?.trim() || draft.ItemName;
    const summary = (pendingProductSpeech[locale] || pendingProductSpeech.en)(spokenName, details);
    return speakText(summary, getTtsLanguage(draft));
  };

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
    const review = {
      Intent: 'inventory_add',
      EntityName: invForm.ItemName.trim(),
      Quantity: Number(invForm.StockQuantity),
      UnitPrice: Number(invForm.Price),
      RawCommand: `Added ${invForm.StockQuantity} ${invForm.ItemName}`,
      LanguageCode: speechLanguage === 'auto' ? 'en-IN' : speechLanguage,
    };
    setPendingReview(review);
    speakReview(review);
    setConfirmationError('');
  };

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    const review = {
      Intent: 'credit_add',
      EntityName: custForm.CustomerName.trim(),
      Quantity: Number(custForm.Amount),
      RawCommand: `Added credit for ${custForm.CustomerName}`,
      LanguageCode: speechLanguage === 'auto' ? 'en-IN' : speechLanguage,
    };
    setPendingReview(review);
    speakReview(review);
    setConfirmationError('');
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
    const selectedItem = pendingItemChoice.Candidates.find(
      item => item.ItemID === selectedItemId
    );
    if (!selectedItem) return;
    const review = {
      Intent: pendingItemChoice.Intent,
      EntityName: selectedItem.ItemName,
      Quantity: pendingItemChoice.Quantity,
      RawCommand: pendingItemChoice.RawCommand,
      LanguageCode: pendingItemChoice.LanguageCode || 'en-IN',
      ItemID: selectedItem.ItemID,
    };
    setPendingReview(review);
    speakReview(review);
    setPendingItemChoice(null);
    setSelectedItemId(null);
    setConfirmationError('');
  };

  const submitTransactionReview = async () => {
    if (!pendingReview) return;
    const quantity = Number(pendingReview.Quantity);
    if (
      !pendingReview.EntityName.trim()
      || !Number.isInteger(quantity)
      || quantity <= 0
      || (
        pendingReview.Intent === 'inventory_add'
        && (!(Number(pendingReview.UnitPrice) > 0) || !Number.isFinite(Number(pendingReview.UnitPrice)))
      )
    ) {
      setConfirmationError(t.invalidTransaction);
      return;
    }
    setConfirmationError('');
    try {
      const isVariant = Number.isInteger(pendingReview.ItemID);
      const response = await fetch(
        isVariant
          ? 'http://127.0.0.1:5000/api/inventory/confirm-command'
          : 'http://127.0.0.1:5000/api/confirm-transaction',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(isVariant
            ? {
                ItemID: pendingReview.ItemID,
                Intent: pendingReview.Intent,
                Quantity: quantity,
                RawCommand: pendingReview.RawCommand,
              }
            : {
                Intent: pendingReview.Intent,
                EntityName: pendingReview.EntityName.trim(),
                Quantity: quantity,
                RawCommand: pendingReview.RawCommand,
                ...(pendingReview.Intent === 'inventory_add'
                  ? { UnitPrice: Number(pendingReview.UnitPrice) }
                  : {}),
              }),
        }
      );
      const result = await response.json();
      if (!response.ok || result.status !== 'success') {
        setConfirmationError(result.error || t.connError);
        return;
      }
      const databaseAction = result.database_action;
      if (databaseAction?.status === 'pending_selection') {
        setPendingReview(null);
        setPendingItemChoice({
          ...databaseAction.draft,
          LanguageCode: pendingReview.LanguageCode,
        });
        setSelectedItemId(null);
        return;
      }
      if (databaseAction?.status === 'pending_confirmation') {
        const draft = databaseAction.draft;
        const options = draft.PriceOptions || (
          Number(draft.Price) > 0
            ? [{ Price: Number(draft.Price), PriceIsMRP: draft.PriceIsMRP, Sources: [] }]
            : []
        );
        setPendingReview(null);
        const productDraft = {
          ...draft,
          LanguageCode: pendingReview.LanguageCode,
          PriceOptions: options.map((option, index) => ({
            ...option,
            Quantity: draft.StockQuantity,
            Selected: index === 0,
          })),
        };
        setPendingDraft(productDraft);
        speakPendingProduct(productDraft);
        setManualMrp('');
        return;
      }
      if (databaseAction?.status !== 'success') {
        setConfirmationError(databaseAction?.message || t.connError);
        return;
      }
      setPendingReview(null);
      setDbAction(databaseAction);
      stopConfirmationAudio();
      if (pendingReview.Intent === 'inventory_add') {
        setInvForm({ ItemName: '', StockQuantity: '', Price: '' });
        setShowAddInv(false);
      } else if (pendingReview.Intent === 'credit_add') {
        setCustForm({ CustomerName: '', Amount: '' });
        setShowAddCust(false);
      }
      fetchDashboardData();
      fetchLedgerData();
    } catch (error) {
      console.error("Transaction confirmation error:", error);
      setConfirmationError(t.connError);
    }
  };

  const searchEditedProductName = async (itemName = pendingDraft?.ItemName) => {
    if (!itemName?.trim()) {
      return;
    }
    const requestedName = itemName.trim();
    setIsSearchingProduct(true);
    setConfirmationError('');
    setPendingDraft(current => current ? ({
      ...current,
      ItemName: requestedName,
      Pronunciation: requestedName === current.ItemName.trim() ? current.Pronunciation : '',
      Price: null,
      PriceFound: false,
      PriceIsMRP: false,
      SearchStatus: 'searching',
      SearchMessage: '',
      SearchResults: [],
      ProductSuggestions: [],
      SuggestionSearchError: false,
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
    if (!pendingDraft) return;
    const options = pendingDraft.PriceOptions || [];
    const updated = {
      ...pendingDraft,
      PriceOptions: options.some(option => Number(option.Price) === price)
        ? options.map(option => (
            Number(option.Price) === price ? { ...option, Selected: true } : option
          ))
        : [
            ...options,
            {
              Price: price,
              PriceIsMRP: false,
              IsManual: true,
              Sources: [],
              Quantity: pendingDraft.StockQuantity,
              Selected: true,
            },
          ],
    };
    setPendingDraft(updated);
    speakPendingProduct(updated);
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
            formData.append('language_code', speechLanguage);

            try {
              const response = await fetch('http://127.0.0.1:5000/api/process-audio', { method: 'POST', body: formData });
              const data = await response.json();
              if (data.status === 'success') {
                setTranscript(data.transcript);
                if (data.database_action?.status === 'pending_review') {
                  const review = {
                    ...data.database_action.draft,
                  };
                  setPendingReview(review);
                  speakReview(review);
                  setConfirmationError('');
                  setIsActive(false);
                  setShowDashboard(true);
                } else if (data.database_action?.status === 'success') {
                  fetchDashboardData();
                  fetchLedgerData();
                  setDbAction(data.database_action);
                  setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 4000);
                } else if (data.database_action && data.database_action.status === 'pending_confirmation') {
                  const draft = data.database_action.draft;
                  const options = draft.PriceOptions || (
                    Number(draft.Price) > 0
                      ? [{ Price: Number(draft.Price), PriceIsMRP: draft.PriceIsMRP, Sources: [] }]
                      : []
                  );
                  const productDraft = {
                    ...draft,
                    LanguageCode: data.language_code,
                    PriceOptions: options.map((option, index) => ({
                      ...option,
                      Quantity: draft.StockQuantity,
                      Selected: index === 0,
                    })),
                  };
                  setPendingDraft(productDraft);
                  speakPendingProduct(productDraft);
                  setManualMrp('');
                  setConfirmationError('');
                  setDbAction({ status: 'pending', message: data.database_action.message });
                  setTimeout(() => { setIsActive(false); setShowDashboard(true); }, 2000);
                } else if (data.database_action?.status === 'pending_selection') {
                  setPendingItemChoice({
                    ...data.database_action.draft,
                    LanguageCode: data.database_action.draft.LanguageCode || data.language_code,
                  });
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
    <div lang={lang} className="flex flex-col w-screen h-screen relative bg-transparent overflow-hidden">
      
      {/* WINDOW CONTROLS HEADER */}
      <header className="overlay-header absolute top-0 left-0 w-full flex justify-between items-center px-4 py-2 bg-gray-900/90 backdrop-blur-md border-b border-gray-700 pointer-events-auto z-50">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-bold text-gray-400 tracking-wider">KIRANASYNC</span>
          <select
            aria-label={t.voiceLanguage}
            title={speechLanguage === 'auto' ? t.autoDetectHint : t.voiceLanguage}
            value={speechLanguage}
            onChange={event => setSpeechLanguage(event.target.value)}
            className="max-w-52 bg-gray-800 text-gray-300 rounded px-2 py-1 text-xs border border-gray-600"
          >
            <option value="auto">{t.autoDetect}</option>
            {voiceLanguages.map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
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
          {pendingReview && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 backdrop-blur-sm pointer-events-auto p-4"
            >
              <motion.div
                initial={{ scale: 0.95, y: 16 }} animate={{ scale: 1, y: 0 }}
                className="bg-gray-800 border border-emerald-500/50 p-6 rounded-2xl shadow-2xl w-full max-w-[440px]"
              >
                <h3 className="text-xl font-bold text-white mb-2">{t.reviewTitle}</h3>
                <p className="text-gray-400 text-sm mb-5">{t.reviewDescription}</p>
                <div className="space-y-4">
                  {pendingReview.Intent === 'inventory_add' ? (
                    <p className="text-xs text-gray-400 font-semibold uppercase">{t.transactionInventoryAdd}</p>
                  ) : pendingReview.Intent === 'credit_add' ? (
                    <p className="text-xs text-gray-400 font-semibold uppercase">{t.transactionCreditAdd}</p>
                  ) : (
                    <label className="block">
                      <span className="text-xs text-gray-400 font-semibold uppercase">{t.transactionAction}</span>
                      <select
                        value={pendingReview.Intent}
                        onChange={event => {
                          const updated = {
                            ...pendingReview,
                            Intent: event.target.value,
                            ItemID: undefined,
                          };
                          setPendingReview(updated);
                          speakReview(updated);
                        }}
                        className="block w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600"
                      >
                        <option value="sell">{t.transactionSell}</option>
                        <option value="restock">{t.transactionRestock}</option>
                        <option value="credit">{t.transactionCredit}</option>
                      </select>
                    </label>
                  )}
                  <label className="block">
                    <span className="text-xs text-gray-400 font-semibold uppercase">{t.transactionEntity}</span>
                    <input
                      type="text"
                      value={pendingReview.EntityName}
                      onChange={event => setPendingReview({
                        ...pendingReview,
                        EntityName: event.target.value,
                        ItemID: undefined,
                      })}
                      onBlur={event => speakReview({
                        ...pendingReview,
                        EntityName: event.target.value,
                        ItemID: undefined,
                      })}
                      className="block w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600"
                    />
                  </label>
                  {pendingReview.Intent === 'inventory_add' && (
                    <label className="block">
                      <span className="text-xs text-gray-400 font-semibold uppercase">{t.transactionPrice}</span>
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={pendingReview.UnitPrice}
                        onChange={event => setPendingReview({
                          ...pendingReview,
                          UnitPrice: event.target.value,
                        })}
                        onBlur={event => speakReview({
                          ...pendingReview,
                          UnitPrice: event.target.value,
                        })}
                        className="block w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600"
                      />
                    </label>
                  )}
                  <label className="block">
                    <span className="text-xs text-gray-400 font-semibold uppercase">{t.transactionQuantity}</span>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={pendingReview.Quantity}
                      onChange={event => setPendingReview({
                        ...pendingReview,
                        Quantity: event.target.value,
                      })}
                      onBlur={event => speakReview({
                        ...pendingReview,
                        Quantity: event.target.value,
                      })}
                      className="block w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600"
                    />
                  </label>
                  {Number(pendingReview.UnitPrice) > 0 && pendingReview.Intent !== 'credit' && (
                    <p className="text-sm text-gray-300">
                      {t.estimatedTotal}: ₹{(
                        Number(pendingReview.UnitPrice) * Number(pendingReview.Quantity)
                      ).toLocaleString('en-IN')}
                    </p>
                  )}
                  {confirmationError && (
                    <p role="alert" className="text-sm text-red-400">{confirmationError}</p>
                  )}
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => {
                      stopConfirmationAudio();
                      setPendingReview(null);
                      setConfirmationError('');
                    }}
                    className="py-3 px-4 rounded-xl bg-gray-700 hover:bg-gray-600 text-gray-300 font-medium"
                  >
                    {t.cancelBtn}
                  </button>
                  <button
                    onClick={() => speakReview(pendingReview)}
                    className="py-3 px-4 rounded-xl bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 font-medium"
                  >
                    {t.readDetails}
                  </button>
                  <button
                    onClick={submitTransactionReview}
                    className="flex-1 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold"
                  >
                    {t.confirmTransaction}
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

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
                          Pronunciation: '',
                          Price: null,
                          PriceFound: false,
                          PriceIsMRP: false,
                          SearchStatus: 'not_searched',
                          SearchResults: [],
                          ProductSuggestions: [],
                          PriceOptions: [],
                        });
                        setConfirmationError('');
                      }}
                      onBlur={event => speakPendingProduct({
                        ...pendingDraft,
                        ItemName: event.target.value,
                      })}
                    />
                    <label className="block text-xs text-gray-400 font-semibold uppercase mt-3">
                      {productPronunciationText[0]}
                    </label>
                    <input
                      type="text"
                      className="w-full bg-gray-700 text-white p-3 rounded-xl mt-1 border border-gray-600 focus:border-blue-500 outline-none"
                      value={pendingDraft.Pronunciation || ''}
                      onChange={event => setPendingDraft({
                        ...pendingDraft,
                        Pronunciation: event.target.value,
                      })}
                      onBlur={() => speakPendingProduct(pendingDraft)}
                    />
                    <p className="text-xs text-gray-500 mt-1">{productPronunciationText[1]}</p>
                    <button
                      type="button"
                      onClick={() => speakPendingProduct(pendingDraft)}
                      className="mt-2 px-3 py-2 rounded-lg bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 text-sm"
                    >
                      {t.readDetails}
                    </button>
                    <button
                      type="button"
                      onClick={() => searchEditedProductName()}
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
                  {pendingDraft.SearchStatus === 'no_relevant_results'
                    && pendingDraft.ProductSuggestions?.length > 0 && (
                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                      <p className="text-xs text-amber-200 mb-2">{t.similarProductNames}</p>
                      <div className="flex flex-wrap gap-2">
                        {pendingDraft.ProductSuggestions.map(name => (
                          <button
                            key={name}
                            type="button"
                            onClick={() => searchEditedProductName(name)}
                            disabled={isSearchingProduct}
                            className="px-3 py-1.5 rounded-lg border border-amber-500/40 text-amber-100 hover:bg-amber-500/15 disabled:opacity-40 text-sm"
                          >
                            {name} · {t.searchSuggestedName}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {pendingDraft.SearchStatus === 'no_relevant_results'
                    && pendingDraft.SuggestionSearchError && (
                    <p role="status" className="text-xs text-amber-300">{t.suggestionSearchError}</p>
                  )}
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
                              onChange={event => {
                                const updated = {
                                  ...pendingDraft,
                                  PriceOptions: pendingDraft.PriceOptions.map((entry, entryIndex) => (
                                    entryIndex === index ? { ...entry, Selected: event.target.checked } : entry
                                  )),
                                };
                                setPendingDraft(updated);
                                speakPendingProduct(updated);
                              }}
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
                                  onBlur={event => speakPendingProduct({
                                    ...pendingDraft,
                                    PriceOptions: pendingDraft.PriceOptions.map((entry, entryIndex) => (
                                      entryIndex === index ? { ...entry, Quantity: event.target.value } : entry
                                    )),
                                  })}
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
                <select
                  aria-label={t.displayLanguage}
                  value={lang}
                  onChange={event => setLang(event.target.value)}
                  className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium border border-gray-600 transition-colors"
                >
                  {displayLanguages.map(([code, name]) => (
                    <option key={code} value={code}>{name}</option>
                  ))}
                </select>
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