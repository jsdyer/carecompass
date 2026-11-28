import {localityKey,matches,loadSaved,saveEntries,safeURL,csv,vacancyLabel} from './model.mjs';
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
$('province').value = config.default_province;
selectValue('province', params.get('province'));
selectValue('community', $('province').value.toLowerCase() + '-' + localityKey(params.get('community')));
for (const name of ['age', 'program', 'hours']) selectValue(name, params.get(name));
function updateCommunities() {
  const province = $('province').value;
  for (const group of $('community').querySelectorAll('optgroup')) {
    group.disabled = !!province && group.firstElementChild?.dataset.province !== province;
    group.hidden = group.disabled;
  }
  if ($('community').selectedOptions[0]?.parentElement.disabled) $('community').value = '';
}
function updateAgeCoverage() {
  const province = $('province').value;
  const separate = data.facilities.some(r => r.province === 'NS' && (r.ages.infant != null || r.ages.toddler != null));
  for (const option of $('age').options) {
    if (!['infant', 'toddler'].includes(option.value)) continue;
    option.hidden = option.disabled = province === 'BC' || !separate;
  }
  if ($('age').selectedOptions[0]?.disabled) $('age').value = '';
  const note = $('age-coverage');
  note.hidden = separate || province === 'BC';
  note.textContent = note.hidden ? '' : 'This capture groups infants and toddlers under “Under 3 years”. Separate Nova Scotia flags were unavailable.';
}
updateAgeCoverage();
updateCommunities();
function updatePublicLink() {
  const current = new URL(location.href);
  for (const name of ['community', 'province', 'age', 'program', 'hours']) current.searchParams.delete(name);
  const selected = $('community').selectedOptions[0];
  if (selected?.value) {
    current.searchParams.set('province', selected.dataset.province);
    current.searchParams.set('community', selected.textContent);
    for (const name of ['age', 'program', 'hours']) if ($(name).value) current.searchParams.set(name, $(name).value);
  }
  history.replaceState(null, '', current);
}

function persist(){const ok=saveEntries(storage,saved);$('storage-status').textContent=ok?'Shortlist saved on this device.':'Browser storage is unavailable. Keep this tab open and export your shortlist.';}
function link(text,url){const a=el('a',text);a.href=safeURL(url)||'#';a.target='_blank';a.rel='noopener noreferrer';return a;}
function card(row){const node=el('article',undefined,'card');node.append(el('span',row.province+' · '+row.type,'eyebrow'),el('h2',row.name),el('p',row.address,'address'));
  const badges=el('div',undefined,'badges');
  const youngAges = row.ages.infant != null || row.ages.toddler != null
    ? [['infant','Infant'],['toddler','Toddler']] : [['under36','Under 3']];
  for(const [k,label] of [...youngAges,['preschool','Preschool'],['school','School age']])if(row.ages[k]===true)badges.append(el('span',label));if(!badges.children.length)badges.append(el('span','Ages not supplied'));node.append(badges);
  node.append(el('p',row.age_range||row.hours),el('p',vacancyLabel(row),'vacancy'),el('p',row.vacancy_updated?'Vacancy information dated '+row.vacancy_updated:'No vacancy update date supplied','small'));
  const details=el('details'),summary=el('summary','Directory details');details.append(summary);if(row.capacity!==null)details.append(el('p','Licensed capacity: '+row.capacity+' (not available places)'));for(const date of row.inspection_dates)details.append(el('p',date.type+' inspection: '+date.date));if(row.languages&&row.languages!=='None')details.append(el('p','Additional languages: '+row.languages));details.append(el('p','Hours: '+row.hours));const inspected=safeURL(row.inspection_url);if(inspected)details.append(link('Official inspection information ↗',inspected));node.append(details);
  const contacts=el('div',undefined,'actions');if(row.phone)contacts.append(el('span','Phone: '+row.phone));const site=safeURL(row.website);if(site)contacts.append(link('Provider website ↗',site));if(row.email&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(row.email)){const a=el('a','Email provider');a.href='mailto:'+row.email;contacts.append(a);}node.append(contacts);
  const button=el('button',saved[row.id]?'Remove from shortlist':'Add to shortlist',saved[row.id]?'quiet':'');button.addEventListener('click',()=>{if(saved[row.id])delete saved[row.id];else saved[row.id]={status:'To contact',note:'',updated:new Date().toISOString()};persist();render();});node.append(button);
  if(saved[row.id]){const form=el('div',undefined,'plan');const label=el('label','Contact status'),select=el('select');for(const status of ['To contact','Contacted','Waitlisted','Visit booked','Place offered','Not a fit']){const o=el('option',status);o.value=status;select.append(o);}select.value=saved[row.id].status;label.append(select);const notes=el('label','Private contact notes'),textarea=el('textarea');textarea.value=saved[row.id].note;textarea.placeholder='Fees, next call, questions…';textarea.maxLength=3000;notes.append(textarea);for(const input of [select,textarea])input.addEventListener('change',()=>{saved[row.id]={status:select.value,note:textarea.value,updated:new Date().toISOString()};persist();});form.append(label,notes);node.append(form);}return node;
}
function render(){const filters={q:$('query').value,province:$('province').value,community:$('community').value,age:$('age').value,program:$('program').value,hours:$('hours').value,vacancy:$('vacancy').value,...($('saved-only').checked?{saved:Object.keys(saved)}:{})};filtered=data.facilities.filter(r=>matches(r,filters));$('results').replaceChildren(...filtered.slice(0,limit).map(card));$('status').textContent=filtered.length.toLocaleString()+' matching facilities · '+Object.keys(saved).length+' in your shortlist';$('more').hidden=filtered.length<=limit;if(!filtered.length)$('results').append(el('p','No facilities match these filters. Try a broader area or clear a service filter: unknown fields do not match a specific service.','notice'));if(map)renderMap();}
function renderMap(){layer.clearLayers();for(const row of filtered){if(!row.coordinates)continue;const node=el('div');node.append(el('strong',row.name),el('p',row.address),el('p',vacancyLabel(row)));L.circleMarker([row.coordinates[1],row.coordinates[0]],{radius:5,color:'#185d51',weight:1,fillOpacity:.7}).bindPopup(node).addTo(layer);}const points=filtered.filter(r=>r.coordinates).map(r=>[r.coordinates[1],r.coordinates[0]]);if(points.length)map.fitBounds(points,{padding:[25,25],maxZoom:13});}
$('show-map').addEventListener('click',()=>{$('map-panel').hidden=!$('map-panel').hidden;if(!$('map-panel').hidden){if(!map){map=L.map('map').setView([49,-97],4);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);layer=L.layerGroup().addTo(map);}map.invalidateSize();renderMap();}$('show-map').textContent=$('map-panel').hidden?'Show map':'Hide map';});
for (const id of ['query','province','community','age','program','hours','vacancy','saved-only']) {
  $(id).addEventListener(id === 'query' ? 'input' : 'change', () => {
    if (id === 'community' && $('community').value) $('province').value = $('community').selectedOptions[0].dataset.province;
    if (id === 'province' || id === 'community') { updateCommunities(); updateAgeCoverage(); }
    if (['province','community','age','program','hours'].includes(id)) updatePublicLink();
    limit = config.page_size;
    render();
  });
}
$('reset').addEventListener('click', () => {
  for (const id of ['query','province','community','age','program','hours','vacancy']) $(id).value = '';
  $('saved-only').checked = false;
  limit = config.page_size;
  updateCommunities();
  updateAgeCoverage();
  updatePublicLink();
  render();
});
$('more').addEventListener('click',()=>{limit+=config.page_size;render();});
$('clear-saved').addEventListener('click',()=>{saved={};persist();render();});$('export').addEventListener('click',()=>{const blob=new Blob([csv(data.facilities,saved)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='carecompass-shortlist.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function renderSources(){ $('sources').replaceChildren();for(const source of data.sources){const section=el('div');section.append(el('h3',source.name+' · '+source.record_count.toLocaleString()+' facilities'),el('p',source.coverage),el('p','Source edition: '+(source.coverage_date||'Not published')+'. Last source update: '+(source.source_updated||'Not published')+'. '+source.frequency+'.','small'),link('Dataset ↗',source.url),document.createTextNode(' · '),link(source.licence,source.licence_url));$('sources').append(section);}$('sources').append(el('p','Complete directory check: '+data.checked_at+'. This check date is not a vacancy update.','small'));}renderSources();render();

$('save-capture').addEventListener('click',()=>{const u=URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'})),a=el('a');a.href=u;a.download='carecompass-directory-'+data.checked_at.slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
$('open-capture').addEventListener('change',async()=>{try{const file=$('open-capture').files[0];if(!file)return;if(file.size>25000000)throw new Error('The capture is too large.');const next=JSON.parse(await file.text());if(next.schema!==1||!Array.isArray(next.facilities)||!Array.isArray(next.sources)||typeof next.checked_at!=='string'||next.facilities.length>20000||next.facilities.some(r=>!r.id||!r.name||!r.ages||!r.programs||!r.operating||!Array.isArray(r.inspection_dates)))throw new Error('This is not a supported directory capture.');data=next;limit=config.page_size;updateAgeCoverage();updatePublicLink();renderSources();render();$('storage-status').textContent='Viewing saved capture from '+data.checked_at+'. Its original dates and coverage are preserved.';}catch(e){$('storage-status').textContent=e.message;}});

} catch { $('status').textContent='The published directory could not load. Reload the page or open an official directory below.'; for(const [name,url] of [['BC Child Care Map','https://catalogue.data.gov.bc.ca/dataset/child-care-map-data'],['Nova Scotia Child Care Directory','https://data.novascotia.ca/Education-Early-Childhood/Child-Care-Directory/3j9v-yimg']]){const a=el('a',name);a.href=url;const p=el('p');p.append(a);$('sources').append(p);} }
