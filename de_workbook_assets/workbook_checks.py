"""Public behavioral checks. They check outputs, boundaries and failure behavior."""
from workbook_support import *
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import timedelta
import pytest
import requests
import gzip, hashlib, inspect
import pyarrow.parquet as pq
import pyarrow.dataset as ds
from sqlalchemy.exc import IntegrityError

URL='https://practice.invalid/tickets'
D=Decimal

def q1(f):
    equal(f(DATA/'shipments.csv'),expected(1))
    with TemporaryDirectory() as d:
        p=Path(d)/'empty.csv'; p.write_text('shipment_id,carrier\n',encoding='utf-8'); equal(f(p),[])

def q2(f):
    rows=fixture('raw_shipments'); before=copy.deepcopy(rows)
    equal(f(rows),expected(2)); equal(rows,before)
    good=rows[0].copy(); good['unit_fee']='0.10'; good['packages']='3'
    output=f([good]); assert output['valid'][0]['unit_fee']==D('.10')
    assert isinstance(output['valid'][0]['unit_fee'],D)
    bad={**good,'unit_fee':'0.001','packages':'1.5','status':'pending'}
    assert f([bad])['rejected'][0]['reasons']==['packages','unit_fee','status']
    bad={**good,'updated_at':'2026-09-01T00:00:00'}
    assert f([bad])['rejected'][0]['reasons']==['updated_at']
    equal(f([]),{'valid':[],'rejected':[]})

def q3(f):
    rows=fixture('valid_shipments'); before=copy.deepcopy(rows)
    equal(f(rows),expected(3)); equal(rows,before)
    a=rows[0]; b={**a,'packages':99}; equal(f([a,b]),[b])
    equal(f([]),[])

def q4(f):
    equal(f(fixture('latest_shipments')),expected(4)); equal(f([]),{})
    a=fixture('latest_shipments')[0]
    equal(f([{**a,'status':'cancelled'}]),{})
    assert all(isinstance(v,D) for v in f([a]).values())

def q5(f):
    iterator=f(DATA/'shipments.csv',4)
    assert hasattr(iterator,'__next__'),'Return an iterator/generator, not a list of batches.'
    batches=list(iterator); assert [len(x) for x in batches]==[4,4,3]
    equal(sum(batches,[]),fixture('raw_shipments'))
    with pytest.raises(ValueError): list(f(DATA/'shipments.csv',0))
    with TemporaryDirectory() as d:
        p=Path(d)/'empty.csv'; p.write_text('shipment_id,carrier\n'); equal(list(f(p,5)),[])

def q6(f):
    f(fee_total)
    def float_bug(fee,n):
        fee_total(fee,n)
        return float(fee)*n
    def zero_bug(fee,n): return fee_total(fee,max(n,1)) if n>=0 else fee_total(fee,n)
    def negative_bug(fee,n): return fee*n
    def truncation_bug(fee,n): return D(int(fee))*n if fee>=0 and n>=0 else fee_total(fee,n)
    for bug in [float_bug,zero_bug,negative_bug,truncation_bug]:
        try: f(bug)
        except (AssertionError,pytest.fail.Exception): pass
        else: raise AssertionError(f'Your tests did not catch {bug.__name__}. Add an assertion or pytest.raises case.')

def q7(f):
    got=f(DATA/'order_updates.csv'); equal(got,expected(7))
    assert pd.api.types.is_integer_dtype(got['quantity'])
    assert pd.api.types.is_integer_dtype(got['unit_price_cents'])
    assert str(got['updated_at'].dt.tz)=='UTC'

def q8(f):
    df=fixture('order_updates'); before=df.copy(deep=True)
    equal(f(df),expected(8)); equal(df,before)
    tie=pd.concat([df.iloc[[0]],df.iloc[[0]].assign(quantity=99)],ignore_index=True)
    assert f(tie).iloc[0]['quantity']==99
    assert f(df.iloc[0:0]).empty

def q9(f):
    df=fixture('current_orders'); products=fixture('products'); before=df.copy(deep=True)
    equal(f(df,products),expected(9)); equal(df,before)
    with pytest.raises(pd.errors.MergeError): f(df,pd.concat([products,products.iloc[[0]]]))

def q10(f):
    df=fixture('enriched_orders'); before=df.copy(deep=True)
    equal(f(df),expected(10)); equal(df,before)
    empty=f(df.iloc[0:0]); assert list(empty.columns)==['category','orders','units','revenue_cents'] and empty.empty

def q11(f):
    df=fixture('current_orders'); before=df.copy(deep=True)
    equal(f(df,'2026-09-01','2026-09-05'),expected(11)); equal(df,before)
    out=f(df.iloc[0:0],'2026-09-01','2026-09-03')
    assert out['revenue_cents'].tolist()==[0,0,0]
    assert out['rolling_3d_mean'].tolist()==[0.,0.,0.]

def q12(f):
    equal(f(fixture('daily_sales'),fixture('settlements')),expected(12))
    left=pd.DataFrame({'date':['2026-01-01'],'revenue_cents':[200]})
    right=pd.DataFrame({'order_date':['2026-01-02'],'settled_cents':[300]})
    equal(f(left,right),pd.DataFrame({'date':['2026-01-01','2026-01-02'],'revenue_cents':[200,0],'settled_cents':[0,300],'difference_cents':[200,-300]}))

def q13(f):
    rows=fixture('tickets'); before=copy.deepcopy(rows)
    equal(f(rows),expected(13)); equal(rows,before)
    equal(f([]),[])

def q14(f):
    equal(f(fixture('latest_flat_tickets')),expected(14))
    equal(f([{'tags':['a','a','b']},{'tags':None}]),{'a':1,'b':1}); equal(f([]),{})

def q15(f):
    s=PageSession(); equal(f(s,URL),s.pages['START'])
    equal(f(s,URL,'page2'),s.pages['page2']); assert s.calls[-1]['params']=={'cursor':'page2'}
    with pytest.raises(requests.HTTPError): f(SequenceSession([(404,{})]),URL)
    with pytest.raises(requests.exceptions.JSONDecodeError): f(SequenceSession([(200,'not-json')]),URL)

def q16(f):
    s=PageSession(); equal(f(s,URL),fixture('tickets')); assert len(s.calls)==3
    s=PageSession({'START':{'results':[],'next_cursor':None}}); equal(f(s,URL),[])
    s=PageSession({'START':{'results':[],'next_cursor':'same'},'same':{'results':[],'next_cursor':'same'}})
    with pytest.raises(ValueError): f(s,URL)

def q17(f):
    s=SequenceSession([(503,{}),requests.Timeout('fixture'),(200,{'results':[],'next_cursor':None})]); delays=[]
    equal(f(s,URL,max_attempts=3,sleep_fn=delays.append),{'results':[],'next_cursor':None})
    assert delays==[1,2],delays
    s=SequenceSession([(401,{})]); delays=[]
    with pytest.raises(requests.HTTPError): f(s,URL,sleep_fn=delays.append)
    assert len(s.calls)==1 and not delays
    s=SequenceSession([(200,'broken-json')]); delays=[]
    with pytest.raises(requests.exceptions.JSONDecodeError): f(s,URL,sleep_fn=delays.append)
    assert len(s.calls)==1 and not delays
    s=SequenceSession([(429,{})]*3)
    with pytest.raises(requests.HTTPError): f(s,URL,sleep_fn=lambda _:None)
    assert len(s.calls)==3

def q18(f):
    watermark=datetime(2026,9,1,0,6,tzinfo=timezone.utc); rows=fixture('tickets'); before=copy.deepcopy(rows)
    equal(f(rows,watermark,3),expected(18)); equal(rows,before)
    equal(f([],watermark,3),{'records':[],'next_watermark':watermark})
    assert [r['id'] for r in f(rows,watermark,0)['records']]==['T4']
    with pytest.raises(ValueError): f(rows,watermark,-1)

def q19(f):
    equal(f(DATA/'apartment_sales.xml'),expected(19))
    with TemporaryDirectory() as d:
        p=Path(d)/'empty.xml'; p.write_text('<sales xmlns="urn:practice:sales"/>'); equal(f(p),[])

def q20(f):
    row=fixture('xml_rows')[0]; before=copy.deepcopy(row)
    equal(f(row),expected(20)); equal(row,before)
    result=f(fixture('xml_rows')[1]); assert result['floor']==-1 and result['cancelled'] is False
    with pytest.raises(ValueError): f({**row,'price_manwon':'not-money'})
    with pytest.raises(ValueError): f({**row,'cancelled':'?'})

def q21(f):
    rows=fixture('normalized_sales'); before=copy.deepcopy(rows)
    equal(f(rows),expected(21)); equal(rows,before)
    extra={**rows[0],'unexpected':1}
    assert f([extra])['rejected']==[{'sale_id':'S01','fields':['unexpected']}]
    boolean={**rows[0],'price_krw':True}
    assert f([boolean])['rejected']==[{'sale_id':'S01','fields':['price_krw']}]
    naive={**rows[0],'updated_at':'2026-09-01T00:00:00'}
    assert f([naive])['rejected']==[{'sale_id':'S01','fields':['updated_at']}]
    equal(f([]),{'valid':[],'rejected':[]})

def q22(f):
    equal(f(fixture('current_sales')),expected(22)); equal(f([]),{})
    row=fixture('current_sales')[0]; equal(f([{**row,'cancelled':True}]),{})

def q23(f):
    rows=fixture('valid_sales'); before=copy.deepcopy(rows)
    equal(f(rows),expected(23)); equal(rows,before)
    equal(f(list(reversed(rows))),expected(23))
    a=rows[0]; b={**a,'cancelled':True}; equal(f([a,b]),[])

def q24(f):
    it=f(DATA/'apartment_sales.xml'); assert hasattr(it,'__next__'),'Return an iterator.'
    equal(list(it),fixture('xml_rows'))
    with TemporaryDirectory() as d:
        p=Path(d)/'empty.xml'; p.write_text('<sales xmlns="urn:practice:sales"/>'); equal(list(f(p)),[])

def q25(f):
    equal(f(DATA/'events.jsonl'),expected(25))
    with TemporaryDirectory() as d:
        p=Path(d)/'empty.jsonl'; p.write_text('\n  \n'); equal(f(p),{'records':[],'rejected':[]})

def q26(f):
    rows=fixture('parsed_events'); before=copy.deepcopy(rows)
    equal(f(rows),expected(26)); equal(rows,before)
    assert f(rows)['valid'][0]['timestamp']==datetime(2026,9,1,tzinfo=timezone.utc)
    invalid=[{'timestamp':None},{'timestamp':'2026-09-01T00:00:00'},{}]
    equal(f(invalid),{'valid':[],'rejected':invalid})

def q27(f):
    rows=fixture('normalized_events'); before=copy.deepcopy(rows)
    equal(f(rows),expected(27)); equal(rows,before)
    a=rows[0]; equal(f([a,{**a,'event_type':'purchase'}]),[a]); equal(f([]),[])

def q28(f):
    rows=fixture('unique_events'); before=copy.deepcopy(rows)
    equal(f(rows),expected(28)); equal(rows,before)
    equal(f(list(reversed(rows))),expected(28)); equal(f([]),[])
    got={r['event_id']:r['session_id'] for r in f(rows)}
    assert got['E4']=='101-1' and got['E5']=='101-2','Exactly 30 minutes stays in the session; 31 starts a new one.'

def q29(f):
    rows=fixture('sessions'); before=copy.deepcopy(rows)
    equal(f(rows),{101:True,205:False,309:False}); equal(rows,before)
    equal(f(list(reversed(rows))),{101:True,205:False,309:False}); equal(f([]),{})
    a=rows[0]; t=a['timestamp']
    mixed=[{**a,'event_type':'view','timestamp':t},{**a,'event_type':'cart','product_id':'OTHER','timestamp':t+timedelta(minutes=1)},{**a,'event_type':'purchase','timestamp':t+timedelta(minutes=2)}]
    equal(f(mixed),{101:False})
    seq=[{**a,'event_id':str(i),'event_type':kind,'timestamp':t+timedelta(minutes=i)} for i,kind in enumerate(['view','cart','view','purchase'])]
    equal(f(seq),{101:True})

def q30(f):
    logger=logging.getLogger('de_workbook_check'); old_handlers=logger.handlers[:]; old_level=logger.level; old_propagate=logger.propagate
    capture=CaptureHandler(); logger.handlers=[capture]; logger.setLevel(logging.INFO); logger.propagate=False
    try:
        result=f(DATA/'events.jsonl',logger); equal(result,expected(30))
        assert len(capture.records)==1 and capture.records[0].levelno==logging.INFO
        equal(json.loads(capture.records[0].getMessage()),{'event':'batch_complete',**result['counts']})
        c=result['counts']; assert c['input_records']==c['accepted']+c['duplicates']+c['parse_rejected']+c['timestamp_rejected']
    finally: logger.handlers=old_handlers; logger.setLevel(old_level); logger.propagate=old_propagate

def q31(f):
    engine=make_engine()
    try:
        equal(f(engine,'SEO'),[{'sku':'A','warehouse':'SEO','qty':10,'version':1,'is_deleted':0},{'sku':'B','warehouse':'SEO','qty':5,'version':1,'is_deleted':0}])
        equal(f(engine,"SEO' OR 1=1 --"),[])
    finally: engine.dispose()

def q32(f):
    engine=make_engine()
    try:
        assert f(engine,[{'run_id':'r1','rows_loaded':3},{'run_id':'r2','rows_loaded':0}])==2
        before=table_rows(engine,'load_audit')
        with pytest.raises(IntegrityError): f(engine,[{'run_id':'r3','rows_loaded':1},{'run_id':'r1','rows_loaded':9}])
        equal(table_rows(engine,'load_audit'),before)
        assert f(engine,[])==0
    finally: engine.dispose()

STOCK_AFTER=[{'sku':'A','warehouse':'BUS','qty':7,'version':1,'is_deleted':0},{'sku':'A','warehouse':'SEO','qty':13,'version':3,'is_deleted':0},{'sku':'B','warehouse':'SEO','qty':0,'version':2,'is_deleted':1},{'sku':'C','warehouse':'SEO','qty':4,'version':1,'is_deleted':0}]
def q33(f):
    engine=make_engine()
    try:
        changes=fixture('stock_changes')
        with engine.begin() as c: f(c,changes)
        equal(table_rows(engine,'inventory'),STOCK_AFTER)
        with engine.begin() as c: f(c,changes)
        equal(table_rows(engine,'inventory'),STOCK_AFTER)
        with pytest.raises(RuntimeError):
            with engine.begin() as c:
                f(c,[{'sku':'X','warehouse':'SEO','qty':1,'version':1,'is_deleted':0}]); raise RuntimeError('rollback test')
        equal(table_rows(engine,'inventory'),STOCK_AFTER)
    finally: engine.dispose()

def q34(f):
    engine=make_engine()
    try:
        equal(f(engine,5),[{'sku':'B','warehouse':'SEO','qty':5}]); equal(f(engine,0),[])
        with engine.begin() as c: c.execute(text("UPDATE inventory SET is_deleted=1 WHERE sku='B'"))
        equal(f(engine,5),[])
    finally: engine.dispose()

def q35(f):
    engine=make_engine()
    try:
        equal(f(engine,2,2),fixture('stock_changes')[2:4]); equal(f(engine,6,2),[])
        with pytest.raises(ValueError): f(engine,0,0)
    finally: engine.dispose()

def q36(f):
    engine=make_engine()
    def fail(): raise RuntimeError('simulated crash after writes')
    try:
        before=table_rows(engine,'inventory')
        with pytest.raises(RuntimeError): f(engine,limit=100,after_apply=fail)
        equal(table_rows(engine,'inventory'),before); assert table_rows(engine,'checkpoint')[0]['last_change_id']==0
        equal(f(engine,limit=2),{'read':2,'checkpoint':2})
        equal(f(engine,limit=100),{'read':4,'checkpoint':6})
        equal(table_rows(engine,'inventory'),STOCK_AFTER)
        equal(f(engine),{'read':0,'checkpoint':6})
    finally: engine.dispose()

def q37(f): equal(f(DATA/'sensors.parquet'),expected(37))

def q38(f):
    start=datetime(2026,9,1,tzinfo=timezone.utc); end=start+timedelta(days=1)
    got=f(DATA/'sensors.parquet','SEO',start,end)
    assert isinstance(got,pa.Table) and got.column_names==['device_id','timestamp','temperature_c']
    equal(got.to_pylist(),expected(38)); assert f(DATA/'sensors.parquet','NONE',start,end).num_rows==0

def q39(f):
    table=fixture('sensors'); equal(f(table),expected(39))
    rows=[{'device_id':'X','site':'SEO','timestamp':datetime(2026,9,1,tzinfo=timezone.utc),'temperature_c':v} for v in [-20.,50.,None,float('inf')]]
    output=f(pa.Table.from_pylist(rows,schema=table.schema))
    assert output['valid'].num_rows==2 and output['rejected']['reason'].to_pylist()==['missing','out_of_range']

def q40(f): equal(f(fixture('valid_sensors')),expected(40))

def q41(f):
    table=fixture('valid_sensors')
    with TemporaryDirectory() as d:
        target=Path(d)/'curated'
        f(table,target); dataset=ds.dataset(target,format='parquet',partitioning='hive'); assert dataset.count_rows()==7
        assert {p.parent.name for p in target.rglob('*.parquet')}=={'event_date=2026-09-01','event_date=2026-09-02'}
        assert all(pq.ParquetFile(p).metadata.row_group(0).column(0).compression=='SNAPPY' for p in target.rglob('*.parquet'))
        f(table,target); assert ds.dataset(target,format='parquet',partitioning='hive').count_rows()==7
        f(table.slice(0,1),target); assert ds.dataset(target,format='parquet',partitioning='hive').count_rows()==4
        f(table.slice(0,0),target); assert ds.dataset(target,format='parquet',partitioning='hive').count_rows()==4

def q42(f):
    with patch.object(pq,'read_table',side_effect=AssertionError('Use ParquetFile.iter_batches, not a full-table read.')),patch.object(pq.ParquetFile,'read',side_effect=AssertionError('Use iter_batches.')):
        equal(f(DATA/'sensors.parquet',2),expected(42)); equal(f(DATA/'sensors.parquet',3),expected(42))
    with pytest.raises(ValueError): f(DATA/'sensors.parquet',0)

def q43(f):
    assert f('raw/day=2026-09-01/a.jsonl')=='2026-09-01'
    assert f('raw/day=2026-09-02/b.jsonl.gz')=='2026-09-02'
    for key in ['raw/day=2026-02-30/a.jsonl','raw/readme.txt','raw/day=2026-09-01/','raw/day=2026-09-01/nested/a.jsonl']:
        assert f(key) is None,key

def q44(f):
    with offline_s3(listing=True) as s3: equal(f(s3,'practice-only','raw/'),expected(44))
    with offline_s3(listing=True,empty=True) as s3: equal(f(s3,'practice-only','raw/'),[])

def q45(f):
    pairs=[('raw/day=2026-09-01/a.jsonl',[{'id':'A1','value':10},{'id':'A2','value':20}]),('raw/day=2026-09-02/b.jsonl.gz',[{'id':'B1','value':30}])]
    for key,wanted in pairs:
        with offline_s3(key=key) as s3:
            equal(f(s3,'practice-only',key),wanted); assert s3._practice_stream.closed,'Close the StreamingBody.'
    key=pairs[0][0]
    with offline_s3(key=key,payload=b'{broken}\n') as s3:
        with pytest.raises(ValueError): f(s3,'practice-only',key)
        assert s3._practice_stream.closed,'Close the body even after a parsing error.'

def q46(f):
    equal(f(DATA/'object_a.jsonl',4),expected(46))
    with TemporaryDirectory() as d:
        p=Path(d)/'empty'; p.write_bytes(b'')
        equal(f(p),{'sha256':hashlib.sha256(b'').hexdigest(),'size':0})
    with pytest.raises(ValueError): f(DATA/'object_a.jsonl',0)

def q47(f):
    objects=fixture('objects'); previous=fixture('previous_manifest'); before=copy.deepcopy(previous)
    equal(f(objects,previous),expected(47)); equal(previous,before)
    equal(f([],{}),{'to_load':[],'unchanged':[],'missing':[]})
    with pytest.raises(ValueError): f(objects+[objects[0]],previous)
    obj={'key':'x','etag':'same','size':2}
    assert f([obj],{'x':{'etag':'same','size':1}})['to_load']==[obj]

def q48(f):
    objects=fixture('objects'); previous=fixture('previous_manifest'); before=copy.deepcopy(previous)
    loaded=[]; saved=[]
    def load(o): loaded.append(o['key']); return 2 if o['key'].endswith('a.jsonl') else 1
    result=f(objects,previous,load,saved.append)
    assert loaded==[objects[0]['key'],objects[2]['key']]
    manifest={o['key']:{'etag':o['etag'],'size':o['size']} for o in objects}
    equal(result,{'loaded':loaded,'rows_loaded':3,'manifest':manifest}); equal(saved,[manifest]); equal(previous,before)
    loaded.clear(); saved.clear()
    equal(f(objects,manifest,load,saved.append),{'loaded':[],'rows_loaded':0,'manifest':manifest}); assert not loaded and len(saved)==1
    saved.clear(); attempted=[]
    def fail_second(o):
        attempted.append(o['key'])
        if len(attempted)==2: raise RuntimeError('sink unavailable')
        return 2
    with pytest.raises(RuntimeError): f(objects,previous,fail_second,saved.append)
    assert saved==[] and len(attempted)==2,'Do not save a manifest after partial failure.'
    saved.clear()
    def bad_save(manifest): raise OSError('checkpoint unavailable')
    with pytest.raises(OSError): f(objects,previous,load,bad_save)

CHECKS={i:globals()[f'q{i}'] for i in range(1,49)}
