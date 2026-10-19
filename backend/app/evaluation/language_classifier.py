import re

def classify_indic_language(text):
    """
    Classifies utterance into:
    - 'Devanagari Hindi': contains Unicode Devanagari characters (\u0900-\u097F)
    - 'Romanized Hinglish': Latin script with Hindi vocabulary / grammar markers
    - 'English': Pure English retail vocabulary
    - 'Code-Mixed': Mix of English brand words and Indic structural grammar
    """
    if re.search(r'[\u0900-\u097F]', text):
        return "Devanagari Hindi"
    
    lower = text.lower()
    indic_markers = {
        'bech', 'becha', 'becho', 'bechi', 'bik', 'bika', 'bikri',
        'kilo', 'cheeni', 'tel', 'namak', 'aaye', 'aayi', 'bhi',
        'udhaar', 'khate', 'jama', 'chukaye', 'lautaye', 'hisaab',
        'batao', 'bataiye', 'bacha', 'bachi', 'khatam', 'samaan',
        'paanch', 'chaar', 'teen', 'dus', 'darjan', 'bhaiya', 'padi',
        'chadhana', 'jodna', 'rupaye', 'rupay'
    }
    english_markers = {
        'sell', 'sold', 'packets', 'packet', 'bottles', 'bottle',
        'restock', 'delivered', 'delivery', 'stock', 'cash', 'credit',
        'payment', 'received', 'paid', 'deposited', 'balance', 'owe',
        'items', 'running', 'today', 'sales', 'collected', 'weather',
        'ignore', 'delete', 'clear'
    }

    words = set(re.findall(r'[a-zA-Z]+', lower))
    has_indic = bool(words & indic_markers)
    has_english = bool(words & english_markers)

    if has_indic and has_english:
        return "Code-Mixed"
    if has_indic:
        return "Romanized Hinglish"
    return "English"
