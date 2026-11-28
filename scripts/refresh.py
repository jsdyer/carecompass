#!/usr/bin/env python3
"""Collect complete public child-care directories; publish only after both validate."""
from datetime import datetime, timezone
from pathlib import Path
import json, re, urllib.request, urllib.parse, time
ROOT = Path(__file__).resolve().parents[1]

def get(url, params=None):
    if params: url += '?' + urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers={'User-Agent':'CoolCode CareCompass/1.0 (+https://coolcode.ca/carecompass/)'})
    with urllib.request.urlopen(req,timeout=60) as r:
        raw=r.read(25_000_001)
    if len(raw)>25_000_000: raise ValueError('Source exceeds response budget')
    result=json.loads(raw)
    if isinstance(result,dict) and 'error' in result: raise ValueError('Source returned an API error')
    return result

def flag(v):
    return True if str(v).lower() in ('y','yes','true') else False if str(v).lower() in ('n','no','false') else None

def clean(v):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]*>','',str(v or ''))).strip()

def url(v):
    v=clean(v)
    return v if urllib.parse.urlsplit(v).scheme in ('https','http') else ''

def coordinates(lon,lat):
    try:
        lon,lat=float(lon),float(lat)
        if -141<lon<-52 and 41<lat<70:return [lon,lat]
    except (ValueError,TypeError):pass
    return None

def bc(row):
    ages={'under36':flag(row.get('SRVC_UNDER36_IND')),'preschool':flag(row.get('SRVC_30MOS_5YRS_IND')),'school':any(flag(row.get(k)) is True for k in ['SRVC_OOS_KINDER_IND','SRVC_OOS_GR1_AGE12_IND'])}
    # All-N defaults plus "None" service description do not establish that a provider offers no care.
    if not any(ages.values()) and row.get('DESC_PROGRAMS_PROVIDED') in (None,'None',''):ages={k:None for k in ages}
    operating={k:flag(row.get(f)) for k,f in {'weekday':'OP_WEEKDAY_IND','weekend':'OP_WEEKEND_IND','overnight':'OP_OVERNIGHT_IND','early':'OP_EXT_WEEKDAY_BEFORE6AM_IND','late':'OP_EXT_WEEKDAY_AFTER7PM_IND'}.items()}
    if not any(operating.values()) and row.get('DESC_HOURS_OF_OPERATION') in (None,'No opening hours',''):operating={k:None for k in operating}
    vd=clean(row.get('VACANCY_LAST_UPDATE_DATE'))
    vd=vd[:4]+'-'+vd[4:6]+'-'+vd[6:8] if re.match(r'^\d{14}',vd) else vd or None
    return {'id':'bc-'+str(row['FACILITY_ID']), 'province':'BC','name':clean(row['OCCUPANT_NAME']),'type':clean(row.get('SERVICE_TYPE_DESC')),'address':clean(row.get('DESC_FULL_ADDRESS')),'city':clean(row.get('LOCALITY')),'postal':clean(row.get('POSTAL_CODE')),'phone':clean(row.get('CONTACT_PHONE')),'email':clean(row.get('CONTACT_EMAIL')),'website':url(row.get('WEBSITE_URL')),'inspection_url':url(row.get('HA_FAC_INSPEC_RPTS_URL')),'coordinates':coordinates(row.get('LONGITUDE'),row.get('LATITUDE')),'ages':ages,'programs':{'preschool':flag(row.get('SRVC_LICPRE_IND')),'full_day':None,'part_day':None,'school':ages['school']},'operating':operating,'hours':clean(row.get('DESC_HOURS_OF_OPERATION')) if any(operating.values()) else 'Not supplied','languages':clean(row.get('DESC_ADDITIONAL_LANGUAGES')),'vacancy':flag(row.get('VACANCY_IND')),'vacancy_updated':vd,'vacancy_by_age':{k:flag(row.get(f)) for k,f in {'under36':'VACANCY_SRVC_UNDER36_IND','preschool':'VACANCY_SRVC_30MOS_5YRS_IND','school':'VACANCY_SRVC_OOS_GR1_AGE12_IND'}.items()},'capacity':None,'inspection_dates':[],'source':'bc'}

def combined_under_three(row):
    flags = [flag(row.get(key)) for key in ("age_infant", "age_toddler")]
    if True in flags:
        return True
    return False if all(value is False for value in flags) else None


def ns(row):
    point=row.get('georeference',{}).get('coordinates',[])
    return {'id':'ns-'+row['facility_identifier'],'province':'NS','name':clean(row['facility_name']),'type':clean(row.get('facility_type')),'address':', '.join(filter(None,[clean(row.get('address')),clean(row.get('city')),clean(row.get('postal'))])),'city':clean(row.get('city')),'postal':clean(row.get('postal')),'phone':clean(row.get('phone')),'email':'','website':'','inspection_url':'https://nsbr-online-services.gov.ns.ca/DCSOnline/ECDS/loadSearchPage.action','coordinates':coordinates(*point) if len(point)==2 else None,'ages':{'infant':flag(row.get('age_infant')),'toddler':flag(row.get('age_toddler')),'under36':combined_under_three(row),'preschool':flag(row.get('age_preschool')),'school':flag(row.get('age_school_age'))},'age_range':clean(row.get('age_range')),'programs':{k:flag(row.get(f)) for k,f in {'full_day':'prog_full_day','part_day':'prog_part_day','school':'prog_school_age'}.items()},'operating':{k:None for k in ['weekday','weekend','overnight','early','late']},'hours':'Not supplied','languages':'','vacancy':None,'vacancy_updated':None,'vacancy_by_age':{},'capacity':int(row['total_licence_capacity']) if row.get('total_licence_capacity','').isdigit() else None,'inspection_dates':[{'type':label,'date':row[k]} for k,label in [('annual_inspection','Annual'),('annual_unannounced_inspection','Unannounced')] if row.get(k)],'source':'ns'}

def collect(config):
    sources=[];records=[]
    for source in config['sources']:
        if source['id']=='bc':
            endpoint=source['endpoint']; ids=get(endpoint,{'where':'1=1','returnIdsOnly':'true','f':'json'})['objectIds']
            if not ids or len(ids)!=len(set(ids)):raise ValueError('BC ID inventory invalid')
            rows=[]
            for start in range(0,len(ids),300):
                data=get(endpoint,{'objectIds':','.join(map(str,ids[start:start+300])),'outFields':'*','returnGeometry':'false','f':'json'})
                if data.get('exceededTransferLimit'):raise ValueError('BC source truncated')
                rows += [f['attributes'] for f in data['features']]
            if {r['SEQUENCE_ID'] for r in rows}!=set(ids) or len(rows)!=len(ids):raise ValueError('Incomplete BC collection')
            normalized=[bc(r) for r in rows]
            detail={**source,'record_count':len(rows),'source_updated':None,'coverage_date':None}
        elif source['id']=='ns':
            endpoint=source['endpoint'];meta=get(source['metadata']);count=int(get(endpoint,{'$select':'count(*)'})[0]['count'])
            rows=[]
            for start in range(0,count,1000):rows+=get(endpoint,{'$limit':1000,'$offset':start,'$order':'facility_identifier'})
            if len(rows)!=count:raise ValueError('Incomplete NS collection')
            normalized=[ns(r) for r in rows]
            detail={**source,'record_count':len(rows),'source_updated':datetime.fromtimestamp(meta['rowsUpdatedAt'],timezone.utc).isoformat(),'coverage_date':meta['metadata']['custom_fields']['Detailed Metadata'].get('Usage Considerations','Not supplied')}
        else:raise ValueError('No reviewed adapter for '+source['id'])
        if len(normalized)<source['minimum_records'] or any(not r['id'] or not r['name'] for r in normalized):raise ValueError('Invalid source records')
        records+=normalized;sources.append(detail)
    if len({r['id'] for r in records})!=len(records):raise ValueError('Duplicate facility identifiers')
    return {'schema':1,'checked_at':datetime.now(timezone.utc).isoformat(),'record_count':len(records),'sources':sources,'facilities':sorted(records,key=lambda r:(r['province'],r['name'].lower(),r['id']))}

if __name__=='__main__':
    data=collect(json.loads((ROOT/'web/config.json').read_text()))
    target=ROOT/'web/data/latest.json';target.parent.mkdir(exist_ok=True)
    # A failure above leaves the previous publication and its real date untouched.
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');temporary.replace(target)
    (ROOT/'web/data/status.json').write_text(json.dumps({k:data[k] for k in ['schema','checked_at','record_count']},indent=2)+'\n')
    print('Collected',data['record_count'],'facilities from',len(data['sources']),'complete sources')
