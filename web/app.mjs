import {localityKey,matches,offersLanguage,loadSaved,saveEntries,safeURL,csv,vacancyLabel} from './model.mjs';
const $=id=>document.getElementById(id),el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
try {
let [config,data]=await Promise.all([fetch('./config.json').then(r=>r.json()),fetch('./data/latest.json').then(r=>r.json())]);
const storage=(()=>{try{return localStorage;}catch{return null;}})();
let saved=loadSaved(storage),limit=config.page_size,filtered=[],map,layer;
const params = new URLSearchParams(location.search);
function selectValue(id, value) {
  const select = $(id);
  if (value && Array.from(select.options).some(option => option.value === value)) select.value = value;
}
const publishedNames = new Map(Array.from($('province').options, o => [o.value, o.textContent]));
let localityKeys;
const serviceParams = ['age', 'program', 'hours', 'language'];
function updateCaptureCoverage() {
  const selected = $('province').value;
  const codes = new Set(data.facilities.map(row => row.province));
  const sources = data.sources.filter(source => codes.has(source.id.toUpperCase()));
  const names = sources.map(source => {
    const code = source.id.toUpperCase();
    return [code, source.province_name || publishedNames.get(code) || code];
  });
  $('province').replaceChildren(new Option('All listed provinces', ''), ...names.map(([code, name]) => new Option(name, code)));
  selectValue('province', selected);
  $('coverage-names').textContent = new Intl.ListFormat('en-CA').format(names.map(([, name]) => name));
  localityKeys = new Set(data.facilities.map(r => r.province.toLowerCase() + '-' + localityKey(r.city)));
}
function updateCommunities() {
  const province = $('province').value;
  for (const group of $('community').querySelectorAll('optgroup')) {
    for (const option of group.children) {
      option.hidden = option.disabled = !localityKeys.has(option.value);
    }
    group.hidden = group.disabled = (!!province && group.firstElementChild?.dataset.province !== province)
      || Array.from(group.children).every(option => option.disabled);
  }
  const selected = $('community').selectedOptions[0];
  if (selected?.disabled || selected?.parentElement.disabled) $('community').value = '';
}
function updateServiceCoverage() {
  const province = $('province').value;
  const rows = province ? data.facilities.filter(r => r.province === province) : data.facilities;
  for (const [id, field] of [['age', 'ages'], ['program', 'programs'], ['hours', 'operating'], ['vacancy', 'vacancy']]) {
    const select = $(id);
    for (const option of select.options) {
      if (!option.value) continue;
      const supplied = id === 'vacancy'
        ? rows.some(r => option.value === 'unknown' ? r.vacancy == null : r.vacancy != null)
        : rows.some(r => r[field][option.value] != null);
      option.hidden = option.disabled = !supplied;
    }
    if (select.selectedOptions[0]?.disabled) select.value = '';
    select.disabled = Array.from(select.options).every(option => !option.value || option.disabled);
    select.options[0].textContent = select.disabled ? 'Not supplied in this directory' :
      {age:'Any age / unknown', program:'Any program', hours:'Any / unknown', vacancy:'Any / unknown'}[id];
  }
  const language = $('language');
  for (const option of language.options) {
    if (option.value) option.hidden = option.disabled = !rows.some(r => offersLanguage(r, option.value));
  }
  $('language-field').hidden = language.disabled = Array.from(language.options).every(o => !o.value || o.disabled);
  if (language.selectedOptions[0]?.disabled) language.value = '';
  const note = $('age-coverage');
  const grouped = rows.some(r => r.ages.under36 != null);
  const separate = rows.some(r => r.ages.infant != null || r.ages.toddler != null);
  note.hidden = (!grouped || separate) && province !== 'NB';
  note.textContent = province === 'NB' ? 'Age groups reflect licensed capacity. Under 3 matches known infant places. Ask providers about toddler care.'
    : 'This directory groups younger children under “Under 3 years”.';
}
updateCaptureCoverage();
selectValue('province', config.default_province);
selectValue('province', params.get('province'));
selectValue('community', $('province').value.toLowerCase() + '-' + localityKey(params.get('community')));
for (const name of serviceParams) selectValue(name, params.get(name));
updateServiceCoverage();
updateCommunities();
function updatePublicLink() {
  const current = new URL(location.href);
  for (const name of ['community', 'province', ...serviceParams]) current.searchParams.delete(name);
  const selected = $('community').selectedOptions[0];
  if ($('province').value) current.searchParams.set('province', $('province').value);
  if (selected?.value) current.searchParams.set('community', selected.textContent);
  for (const name of serviceParams) if ($(name).value) current.searchParams.set(name, $(name).value);
  history.replaceState(null, '', current);
}

function persist(){const ok=saveEntries(storage,saved);$('storage-status').textContent=ok?'Shortlist saved on this device.':'Browser storage is unavailable. Keep this tab open and export your shortlist.';}
function link(text,url){const a=el('a',text);a.href=safeURL(url)||'#';a.target='_blank';a.rel='noopener noreferrer';return a;}
function card(row){const node=el('article',undefined,'card');node.append(el('span',[row.province,row.type].filter(Boolean).join(' · '),'eyebrow'),el('h2',row.name),el('p',row.address,'address'));
  const badges=el('div',undefined,'badges');
  const youngAges = row.ages.infant != null || row.ages.toddler != null
    ? [['infant','Infant'],['toddler','Toddler']] : [['under36','Under 3']];
  for(const [k,label] of [...youngAges,['preschool','Preschool'],['school','School age']])if(row.ages[k]===true)badges.append(el('span',label));if(!badges.children.length)badges.append(el('span',Object.values(row.ages).some(value=>value != null)?'No age group confirmed':'Ages not supplied'));node.append(badges);
  if(row.age_range || (row.hours && row.hours !== 'Not supplied')) node.append(el('p',row.age_range || row.hours));
  node.append(el('p',vacancyLabel(row),'vacancy'));
  if(row.vacancy != null) node.append(el('p',row.vacancy_updated?'Vacancy information dated '+row.vacancy_updated:'No vacancy update date supplied','small'));
  const details = el('details');
  details.append(el('summary','Directory details'));
  if (row.capacity != null) details.append(el('p','Licensed capacity: '+row.capacity+' (not available places)'));
  if (row.capacity_by_age) {
    const counts = [['infant','Infant'],['preschool','Preschool'],['school','School age']]
      .filter(([key]) => Number.isInteger(row.capacity_by_age[key]))
      .map(([key, label]) => label+' '+row.capacity_by_age[key]);
    if (counts.length) details.append(el('p','Licensed places by age: '+counts.join(' · ')));
  }
  for (const date of row.inspection_dates) details.append(el('p',date.type+' inspection: '+date.date));
  if (row.languages && row.languages !== 'None') details.append(el('p',(row.province === 'NB' ? 'Language of service: ' : 'Additional languages: ')+row.languages));
  details.append(el('p','Hours: '+row.hours));
  const inspected=safeURL(row.inspection_url);
  if (inspected) details.append(link('Official inspection information ↗',inspected));
  node.append(details);
  const contacts=el('div',undefined,'actions');if(row.phone)contacts.append(el('span','Phone: '+row.phone));const site=safeURL(row.website);if(site)contacts.append(link('Provider website ↗',site));if(row.email&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email)){const a=el('a','Email provider');a.href='mailto:'+row.email;contacts.append(a);}node.append(contacts);
  const button=el('button',saved[row.id]?'Remove from shortlist':'Add to shortlist',saved[row.id]?'quiet':'');button.addEventListener('click',()=>{if(saved[row.id])delete saved[row.id];else saved[row.id]={status:'To contact',note:'',updated:new Date().toISOString()};persist();render();});node.append(button);
  if(saved[row.id]){const form=el('div',undefined,'plan');const label=el('label','Contact status'),select=el('select');for(const status of ['To contact','Contacted','Waitlisted','Visit booked','Place offered','Not a fit']){const o=el('option',status);o.value=status;select.append(o);}select.value=saved[row.id].status;label.append(select);const notes=el('label','Private contact notes'),textarea=el('textarea');textarea.value=saved[row.id].note;textarea.placeholder='Fees, next call, questions…';textarea.maxLength=3000;notes.append(textarea);for(const input of [select,textarea])input.addEventListener('change',()=>{saved[row.id]={status:select.value,note:textarea.value,updated:new Date().toISOString()};persist();});form.append(label,notes);node.append(form);}return node;
}
function render(){const filters={q:$('query').value,province:$('province').value,community:$('community').value,age:$('age').value,program:$('program').value,hours:$('hours').value,language:$('language').value,vacancy:$('vacancy').value,...($('saved-only').checked?{saved:Object.keys(saved)}:{})};filtered=data.facilities.filter(r=>matches(r,filters));$('results').replaceChildren(...filtered.slice(0,limit).map(card));$('status').textContent=filtered.length.toLocaleString()+' matching facilities · '+Object.keys(saved).length+' in your shortlist';$('more').hidden=filtered.length<=limit;if(!filtered.length)$('results').append(el('p','No facilities match these filters. Try a broader area or clear a service filter: unknown fields do not match a specific service.','notice'));if(map)renderMap();}
function renderMap(){layer.clearLayers();for(const row of filtered){if(!row.coordinates)continue;const node=el('div');node.append(el('strong',row.name),el('p',row.address),el('p',vacancyLabel(row)));L.circleMarker([row.coordinates[1],row.coordinates[0]],{radius:5,color:'#185d51',weight:1,fillOpacity:.7}).bindPopup(node).addTo(layer);}const points=filtered.filter(r=>r.coordinates).map(r=>[r.coordinates[1],r.coordinates[0]]);$('map').hidden = points.length === 0;
  $('map-status').textContent = points.length ? points.length.toLocaleString()+' of '+filtered.length.toLocaleString()+' matching facilities have map points.'
    : 'No map points are available for the current results.';
  if(points.length){map.invalidateSize();map.fitBounds(points,{padding:[25,25],maxZoom:13});}}
$('show-map').addEventListener('click',()=>{$('map-panel').hidden=!$('map-panel').hidden;if(!$('map-panel').hidden){if(!map){map=L.map('map').setView([49,-97],4);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);layer=L.layerGroup().addTo(map);}map.invalidateSize();renderMap();}$('show-map').textContent=$('map-panel').hidden?'Show map':'Hide map';});
for (const id of ['query','province','community',...serviceParams,'vacancy','saved-only']) {
  $(id).addEventListener(id === 'query' ? 'input' : 'change', () => {
    if (id === 'community' && $('community').value) $('province').value = $('community').selectedOptions[0].dataset.province;
    if (id === 'language' && $('language').value && !$('province').value) $('province').value = 'NB';
    if (id === 'province' || id === 'community' || id === 'language') { updateCommunities(); updateServiceCoverage(); }
    if (['province','community', ...serviceParams].includes(id)) updatePublicLink();
    limit = config.page_size;
    render();
  });
}
$('reset').addEventListener('click', () => {
  for (const id of ['query','province','community',...serviceParams,'vacancy']) $(id).value = '';
  $('saved-only').checked = false;
  limit = config.page_size;
  updateCommunities();
  updateServiceCoverage();
  updatePublicLink();
  render();
});
$('more').addEventListener('click',()=>{limit+=config.page_size;render();});
$('clear-saved').addEventListener('click',()=>{saved={};persist();render();});$('export').addEventListener('click',()=>{const blob=new Blob([csv(data.facilities,saved)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='carecompass-shortlist.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function renderSources() {
  $('sources').replaceChildren();
  for (const source of data.sources) {
    const section = el('div');
    section.append(el('h3',source.name+' · '+source.record_count.toLocaleString()+' facilities'), el('p',source.coverage),
      el('p','Source edition: '+(source.coverage_date||'Not published')+'. Last source update: '+(source.source_updated||'Not published')+'. '+source.frequency+'.','small'),
      link('Dataset ↗',source.url), document.createTextNode(' · '), link(source.licence,source.licence_url));
    if (source.sites_url) {
      const sites = el('p');
      sites.append(document.createTextNode('Contact and map details: '), link(source.sites_name, source.sites_url));
      if (source.sites_source_updated) sites.append(document.createTextNode(' · Updated '+source.sites_source_updated.slice(0,10)));
      section.append(sites);
    }
    $('sources').append(section);
  }
  $('sources').append(el('p','Complete directory check: '+data.checked_at+'. This check date is not a vacancy update.','small'));
}
renderSources();
render();

$('save-capture').addEventListener('click',()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'})),a=el('a');a.href=u;a.download='carecompass-directory-'+data.checked_at.slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
$('open-capture').addEventListener('change',async()=>{try{const file=$('open-capture').files[0];if(!file)return;if(file.size>25000000)throw new Error('The capture is too large.');const next=JSON.parse(await file.text());if(next.schema!==1||!Array.isArray(next.facilities)||!Array.isArray(next.sources)||typeof next.checked_at!=='string'||next.facilities.length>20000||next.facilities.some(r=>!r.id||!r.name||!r.ages||!r.programs||!r.operating||!Array.isArray(r.inspection_dates)))throw new Error('This is not a supported directory capture.');data=next;limit=config.page_size;updateCaptureCoverage();updateCommunities();updateServiceCoverage();updatePublicLink();renderSources();render();$('storage-status').textContent='Viewing saved capture from '+data.checked_at+'. Its original dates and coverage are preserved.';}catch(e){$('storage-status').textContent=e.message;}});

} catch { $('status').textContent='The published directory could not load. Reload the page or open an official directory below.'; }
