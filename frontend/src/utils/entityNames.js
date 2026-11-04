export function getEntityName(entity, displayMode, englishKey = 'ItemName', hindiKey = 'ItemNameHindi') {
  const english = entity?.[englishKey] || '';
  const hindi = entity?.[hindiKey] || '';
  return displayMode === 'hi' && hindi ? hindi : english;
}
