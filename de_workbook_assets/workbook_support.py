"""Dataset setup, offline service doubles and public checks. No exercise solutions."""
from pathlib import Path
from datetime import datetime, date, timezone
from decimal import Decimal
from contextlib import contextmanager
import copy, io, json, sqlite3, logging
import pandas as pd
import pyarrow as pa
import requests
from sqlalchemy import create_engine, text
from botocore.stub import Stubber
from botocore.response import StreamingBody
import boto3

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
CHECK_RESULTS={}

def _decode(obj):
    if '__int_key_dict__' in obj: return {int(k):v for k,v in obj['__int_key_dict__'].items()}
    if '__decimal__' in obj: return Decimal(obj['__decimal__'])
    if '__datetime__' in obj: return datetime.fromisoformat(obj['__datetime__'])
    if '__date__' in obj: return date.fromisoformat(obj['__date__'])
    if '__dataframe__' in obj: return pd.DataFrame(obj['__dataframe__'],columns=obj['columns'])
    if '__arrow__' in obj:
        schema=pa.schema([('device_id',pa.string()),('site',pa.string()),('timestamp',pa.timestamp('us',tz='UTC')),('temperature_c',pa.float64())])
        if obj['schema_kind']=='rejected': schema=schema.append(pa.field('reason',pa.string()))
        return pa.Table.from_pylist(obj['__arrow__'],schema=schema)
    return obj

def fixture(name):
    """Return a fresh prepared input so questions can be attempted independently."""
    return json.loads((ROOT/'handoffs/fixtures.json').read_text(encoding='utf-8'),object_hook=_decode)[name]

def expected(number):
    return json.loads((ROOT/'handoffs/expected.json').read_text(encoding='utf-8'),object_hook=_decode)[str(number)]

def equal(actual,wanted):
    """Compare logical outputs; DataFrame index and dtype spelling are not graded."""
    if isinstance(wanted,pd.DataFrame):
        assert isinstance(actual,pd.DataFrame),'Return a pandas DataFrame.'
        pd.testing.assert_frame_equal(actual.reset_index(drop=True),wanted.reset_index(drop=True),check_dtype=False,check_exact=False,rtol=1e-9,atol=1e-9)
    elif isinstance(wanted,pa.Table):
        assert isinstance(actual,pa.Table),'Return a pyarrow.Table.'
        assert actual.column_names==wanted.column_names,(actual.column_names,wanted.column_names)
        assert actual.to_pylist()==wanted.to_pylist(),(actual.to_pylist(),wanted.to_pylist())
    elif isinstance(wanted,dict):
        assert isinstance(actual,dict) and actual.keys()==wanted.keys(),f'Dictionary keys differ: {getattr(actual,"keys",lambda:[])()} vs {wanted.keys()}'
        for key in wanted: equal(actual[key],wanted[key])
    else:
        assert actual==wanted,f'Expected {wanted!r}; got {actual!r}'

def make_engine():
    """Fresh, isolated SQLite database copied from the supplied fixture."""
    engine=create_engine('sqlite://')
    raw=engine.raw_connection()
    with sqlite3.connect(DATA/'warehouse.sqlite') as source:
        source.backup(raw.driver_connection)
    raw.close()
    return engine

def table_rows(engine,name):
    # Identifiers below are a fixed local allowlist, never arbitrary user text.
    orders={'inventory':'warehouse,sku','load_audit':'run_id','checkpoint':'pipeline','source_changes':'change_id'}
    if name not in orders: raise ValueError('Unknown fixture table')
    with engine.connect() as c: return [dict(row) for row in c.execute(text(f'SELECT * FROM {name} ORDER BY {orders[name]}')).mappings()]

class PageSession:
    """requests.Session-shaped local test double. Never sends an HTTP request."""
    def __init__(self,pages=None):
        self.pages=pages or json.loads((DATA/'ticket_pages.json').read_text())
        self.calls=[]
    def get(self,url,params=None,timeout=None):
        assert timeout==5,'Pass timeout=5.'
        params={} if params is None else params
        self.calls.append({'url':url,'params':copy.deepcopy(params),'timeout':timeout})
        assert url=='https://practice.invalid/tickets','Use the supplied URL.'
        key=params.get('cursor','START')
        return response(200,self.pages[key],url)

def response(status,payload,url='https://practice.invalid/tickets'):
    result=requests.Response(); result.status_code=status; result.url=url
    result.reason='fixture response'; result.encoding='utf-8'
    result._content=(json.dumps(payload) if not isinstance(payload,str) else payload).encode('utf-8')
    return result

class SequenceSession:
    def __init__(self,outcomes): self.outcomes=list(outcomes); self.calls=[]
    def get(self,url,params=None,timeout=None):
        assert timeout==5,'Pass timeout=5.'
        self.calls.append({'url':url,'params':params,'timeout':timeout})
        assert self.outcomes,'Too many requests or incorrect retry policy.'
        item=self.outcomes.pop(0)
        if isinstance(item,Exception): raise item
        return response(item[0],item[1],url)

def fee_total(unit_fee,packages):
    """Existing team utility for Q6; Decimal fee, integer count, both >=0."""
    if unit_fee<0 or packages<0: raise ValueError('negative fee/count')
    return unit_fee*packages

@contextmanager
def offline_s3(listing=False,key=None,payload=None,empty=False):
    """Actual boto3 client, with botocore Stubber intercepting every call."""
    client=boto3.client('s3',region_name='ap-northeast-2',aws_access_key_id='OFFLINE',aws_secret_access_key='OFFLINE',endpoint_url='https://practice.invalid')
    with Stubber(client) as stub:
        if listing:
            rows=fixture('s3_listing')
            if empty: stub.add_response('list_objects_v2',{'IsTruncated':False},{'Bucket':'practice-only','Prefix':'raw/'})
            else:
                stub.add_response('list_objects_v2',{'IsTruncated':True,'Contents':rows[:3],'NextContinuationToken':'NEXT'},{'Bucket':'practice-only','Prefix':'raw/'})
                stub.add_response('list_objects_v2',{'IsTruncated':False,'Contents':rows[3:]},{'Bucket':'practice-only','Prefix':'raw/','ContinuationToken':'NEXT'})
        if key is not None:
            if payload is None:
                file_map={'raw/day=2026-09-01/a.jsonl':'object_a.jsonl','raw/day=2026-09-02/b.jsonl.gz':'object_b.jsonl.gz','raw/day=2026-09-03/c.jsonl':'object_c.jsonl'}
                payload=(DATA/file_map[key]).read_bytes()
            stream=io.BytesIO(payload)
            stub.add_response('get_object',{'Body':StreamingBody(stream,len(payload))},{'Bucket':'practice-only','Key':key})
            client._practice_stream=stream
        yield client
        stub.assert_no_pending_responses()

class CaptureHandler(logging.Handler):
    def __init__(self): super().__init__(); self.records=[]
    def emit(self,record): self.records.append(record)

def check(number,function):
    """Run after attempting a question. Unfinished functions are safely skipped."""
    from workbook_checks import CHECKS
    try:
        CHECKS[number](function)
    except NotImplementedError:
        CHECK_RESULTS[number]='not attempted'
        print(f'Q{number:02d}: not implemented yet. Edit its starter cell, then rerun this check.')
        return False
    CHECK_RESULTS[number]='passed'
    print(f'Q{number:02d}: checks passed. Explain the edge cases and scaling trade-off before moving on.')
    return True

def progress():
    passed=sorted(k for k,v in CHECK_RESULTS.items() if v=='passed')
    print(f'{len(passed)}/48 checked in this kernel session; your saved notebook is the durable record.')
    print('Passed:',', '.join(f'Q{k:02d}' for k in passed) or 'none yet')
