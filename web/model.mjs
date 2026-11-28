export const STORAGE_KEY='coolcode:carecompass:shortlist';
export function safeURL(value){try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password?u.href:'';}catch{return '';}}
export function localityKey(value) {
  return String(value || '').trim().replace(/,\s*(?:(?:AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT)\.?)?\s*$/i, '')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
export function offersLanguage(row, language) {
  if (row.province !== 'NB') return false;
  const published = String(row.languages || '').trim().toLowerCase();
  return published === language || (published === 'bilingual' && ['english', 'french'].includes(language));
}
export function matches(row,filters){
  const fold = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s/g,'');
  const q=fold(filters.q || '');
  const hay=fold([row.name,row.address,row.city,row.postal].join(' '));
  const inCommunity = !filters.community || row.province.toLowerCase() + '-' + localityKey(row.city) === filters.community;
  return (!filters.language || offersLanguage(row, filters.language)) && inCommunity && (!q||hay.includes(q))&&(!filters.province||row.province===filters.province)&&(!filters.age||row.ages[filters.age]===true)&&(!filters.program||row.programs[filters.program]===true)&&(!filters.hours||row.operating[filters.hours]===true)&&(!filters.vacancy||filters.vacancy==='reported'&&row.vacancy===true||filters.vacancy==='unknown'&&row.vacancy===null)&&(!filters.saved||filters.saved.includes(row.id));
}
export function loadSaved(storage){try{const data=JSON.parse(storage.getItem(STORAGE_KEY)||'{}');return data&&typeof data==='object'&&!Array.isArray(data)?Object.fromEntries(Object.entries(data).filter(([id,v])=>/^[a-z]{2}-[\w-]+$/.test(id)&&v&&typeof v==='object').map(([id,v])=>[id,{status:String(v.status||'To contact').slice(0,80),note:String(v.note||'').slice(0,3000),updated:String(v.updated||'')}])):{};}catch{return {};}}
export function saveEntries(storage,entries){try{storage.setItem(STORAGE_KEY,JSON.stringify(entries));return true;}catch{return false;}}
export function csv(rows,saved){const quote=v=>'"'+String(v??'').replace(/^[\s]*[=+@-]/,"'$&").replaceAll('"','""')+'"';return [['Name','Province','Address','Phone','Contact status','Private note'],...rows.filter(r=>saved[r.id]).map(r=>[r.name,r.province,r.address,r.phone,saved[r.id].status,saved[r.id].note])].map(row=>row.map(quote).join(',')).join('\r\n');}
export function vacancyLabel(row){return row.vacancy===null?'Vacancy not supplied':row.vacancy?'Vacancy reported — confirm directly':'No vacancy reported — confirm directly';}
