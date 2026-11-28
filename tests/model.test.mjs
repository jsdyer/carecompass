import test from 'node:test';import assert from 'node:assert/strict';import {matches,loadSaved,saveEntries,csv,safeURL,vacancyLabel} from '../web/model.mjs';
const row={id:'ns-123',province:'NS',name:'A New Provider',address:'15 Main Street',city:'Halifax',postal:'B3J 1A1',phone:'902',ages:{under36:true,preschool:null},programs:{full_day:true},operating:{weekend:null},vacancy:null};
test('arbitrary provider and postal input are searched without a preset whitelist',()=>{assert.ok(matches(row,{q:'new provider'}));assert.ok(matches(row,{q:'b3j1a1'}));assert.ok(!matches(row,{q:'elsewhere'}));});
test('unknown service and vacancy never pass a positive filter',()=>{assert.ok(matches(row,{age:'under36'}));assert.ok(!matches(row,{age:'preschool'}));assert.ok(!matches(row,{hours:'weekend'}));assert.ok(matches(row,{vacancy:'unknown'}));assert.ok(!matches(row,{vacancy:'reported'}));assert.equal(vacancyLabel(row),'Vacancy not supplied');});
test('shortlist persists explicitly, rejects invalid structures and reports quota failures',()=>{let value;const s={getItem:()=>value,setItem:(k,v)=>value=v};assert.deepEqual(loadSaved(s),{});const saved={'ns-123':{status:'Waitlisted',note:'Call Tuesday'}};assert.ok(saveEntries(s,saved));assert.equal(loadSaved(s)['ns-123'].note,'Call Tuesday');assert.equal(saveEntries({setItem(){throw Error('quota');}},saved),false);assert.deepEqual(loadSaved(null),{});value='[]';assert.deepEqual(loadSaved(s),{});});
test('safe external URLs and exported notes cannot become script/formula content',()=>{assert.equal(safeURL('javascript:alert(1)'),'');assert.equal(safeURL('https://user:password@example.com'),'');assert.equal(safeURL('https://example.com'),'https://example.com/');assert.match(csv([row],{'ns-123':{status:'To contact',note:'=SUM(1,2)'}}),/"'=SUM\(1,2\)"/);});
test('community links match source locality and province rather than address words',()=>{
  assert.ok(matches({...row,province:'BC',city:'  Langley,BC'}, {community:'bc-langley'}));
  assert.ok(!matches({...row,province:'BC',city:'Fort Langley'}, {community:'bc-langley'}));
  assert.ok(!matches({...row,address:'15 Halifax Road',city:'Bedford'}, {community:'ns-halifax'}));
  assert.ok(!matches(row, {age:'infant'}));
  assert.ok(matches({...row,ages:{infant:true,toddler:false}}, {age:'infant',community:'ns-halifax'}));
});

test('bilingual New Brunswick listings are searchable and shortlist notes survive a reload', () => {
  const facility = {...row, id:'nb-2817', province:'NB', name:'Garderie Étoile', city:'Tracadie, NB'};
  assert.ok(matches(facility, {q:'garderie etoile', community:'nb-tracadie', province:'NB'}));
  const storage = {getItem:() => JSON.stringify({'nb-2817':{note:'Ask about September'}})};
  assert.equal(loadSaved(storage)['nb-2817'].note, 'Ask about September');
});

test('language of service includes bilingual NB providers and excludes other source meanings', () => {
  const english = {...row, province:'NB', languages:'English'};
  const bilingual = {...english, languages:'Bilingual'};
  assert.ok(matches(english, {language:'english'}));
  assert.ok(!matches(english, {language:'french'}));
  for (const language of ['english','french','bilingual']) assert.ok(matches(bilingual, {language}));
  assert.ok(!matches({...row,province:'BC',languages:'French'}, {language:'french'}));
  assert.ok(!matches(row, {language:'english'}));
  assert.ok(matches(row, {language:''}));
});
