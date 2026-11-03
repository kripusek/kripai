"""MCP czasu: prawdziwy przypięty dostawca, awarie, snapshot i granice uprawnień."""
import base64,copy,json,sys,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from app import config,mcp_time,tools
from app.network import ToolError,policy
from app.mcp_client import StdioClient
from scripts import setup_mcp_time as setup


def now_record():
    value=datetime.now(timezone.utc).replace(microsecond=0)
    return {'timezone':'UTC','datetime':value.isoformat(),'day_of_week':('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')[value.weekday()],'is_dst':False}


class FakeClient:
    value=None;catalog=None;closed=False
    def __init__(self,*args,**kwargs):self.args=args;self.kwargs=kwargs;FakeClient.closed=False
    def initialize(self,required):
        return self.catalog or {'tools':[{'name':name,'annotations':{'readOnlyHint':True}} for name in mcp_time.READ_TOOLS]}
    def request(self,method,arguments):
        value=self.value if self.value is not None else now_record()
        return {'structuredContent':value,'content':[{'type':'text','text':json.dumps(value)}]}
    def close(self):FakeClient.closed=True


class TimeTests(unittest.TestCase):
    def setUp(self):
        FakeClient.value=FakeClient.catalog=None
        self.runtime=patch.object(setup,'installed',return_value=config.ROOT/'runtime'/setup.DIRECTORY);self.runtime.start();self.addCleanup(self.runtime.stop)
        self.client=patch.object(mcp_time,'StdioClient',FakeClient);self.client.start();self.addCleanup(self.client.stop)

    def test_now_snapshot_roundtrip_and_source_is_immutable_data(self):
        result=mcp_time.execute({'action':'now','timezone':'UTC'})
        self.assertEqual(result['content_kind'],'time_snapshot')
        self.assertTrue(result['url'].startswith('/api/v1/integrations/mcp-time/result?data='))
        payload=result['url'].split('data=',1)[1];snapshot=mcp_time.decode(payload)
        self.assertEqual(snapshot['result']['timezone'],'UTC')
        self.assertEqual(mcp_time.encode(snapshot),payload)
        self.assertIn('nie odczytuje bieżącego czasu',result['scope_note'])
        self.assertTrue(FakeClient.closed)

    def test_conversion_preserves_instant_and_reports_today_limit(self):
        source={'timezone':'Europe/Warsaw','datetime':'2026-11-03T09:30:00+01:00','day_of_week':'Tuesday','is_dst':False}
        target=dict(source,timezone='America/New_York',datetime='2026-11-03T03:30:00-05:00')
        FakeClient.value={'source':source,'target':target,'time_difference':'-6.0h'}
        result=mcp_time.execute({'action':'convert','timezone':'Europe/Warsaw','target_timezone':'America/New_York','time':'09:30'})
        self.assertIn('dzisiejszej daty',result['text'])
        self.assertFalse(result['truncated'])
        FakeClient.value['time_difference']='+8.0h'
        with self.assertRaises(ToolError):mcp_time.execute({'action':'convert','timezone':'Europe/Warsaw','target_timezone':'America/New_York','time':'09:30'})

    def test_bad_zones_actions_times_and_extra_date_never_spawn(self):
        cases=[{'timezone':'../private'}, {'timezone':'C:\\secret'}, {'action':'write'}, {'action':'now','time':'09:30'}, {'action':'convert','target_timezone':'UTC','time':'25:01'}, {'action':'convert','target_timezone':'UTC','time':'9:30'}, {'action':'now','date':'2027-01-01'}]
        with patch.object(mcp_time,'StdioClient',side_effect=AssertionError('No child')):
            for args in cases:
                with self.subTest(args=args),self.assertRaises(ToolError):mcp_time.execute(args)

    def test_missing_runtime_and_mcp_consent_do_not_grant_a_tool(self):
        with patch.object(setup,'installed',return_value=None),self.assertRaises(ToolError) as error:mcp_time.execute({'timezone':'UTC'})
        self.assertEqual(error.exception.code,'mcp_time_unavailable')
        self.assertFalse(any(row['function']['name']=='mcp_time' for row in tools.schemas(policy('time'))))
        scope=tools.bind_integrations(policy('time',mcp=True))
        self.assertTrue(any(row['function']['name']=='mcp_time' for row in tools.schemas(scope)))
        from app.integrations import read
        with self.assertRaises(ToolError):read('mcp_time',{'timezone':'UTC'},policy('time'))

    def test_wrong_timezone_stale_clock_and_malformed_types_rejected_and_closed(self):
        for key,value in [('timezone','Europe/Warsaw'),('is_dst','false'),('datetime',(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()),('day_of_week','not-a-day')]:
            FakeClient.value=dict(now_record(),**{key:value})
            with self.subTest(key=key),self.assertRaises(ToolError):mcp_time.execute({'timezone':'UTC'})
            self.assertTrue(FakeClient.closed)
        FakeClient.value={'timezone':'UTC'}
        with self.assertRaises(ToolError):mcp_time.execute({'timezone':'UTC'})

    def test_catalog_requires_only_known_readonly_tools(self):
        for catalog in [{'tools':[{'name':'shell','annotations':{'readOnlyHint':True}}]}, {'tools':[{'name':name,'annotations':{'readOnlyHint':False}} for name in mcp_time.READ_TOOLS]}, {'tools':[{'name':name,'annotations':None} for name in mcp_time.READ_TOOLS]}]:
            FakeClient.catalog=catalog
            with self.subTest(catalog=catalog),self.assertRaises(ToolError):mcp_time.execute({'timezone':'UTC'})
            self.assertTrue(FakeClient.closed)

    def test_structured_and_text_disagreement_and_remote_error_fail(self):
        with patch.object(FakeClient,'request',return_value={'structuredContent':now_record(),'content':[{'type':'text','text':'{}'}]}),self.assertRaises(ToolError):mcp_time.execute({'timezone':'UTC'})
        with patch.object(FakeClient,'request',return_value={'isError':True}),self.assertRaises(ToolError) as error:mcp_time.execute({'timezone':'UTC'})
        self.assertEqual(error.exception.code,'mcp_time_arguments_invalid')

    def test_bad_snapshot_does_not_open_arbitrary_data_or_paths(self):
        for value in ['../file','x'*1801,'invalid','aGVsbG8',base64.urlsafe_b64encode(b'{"action":"shell"}').decode().rstrip('=')]:
            with self.subTest(value=value[:20]),self.assertRaises(ToolError):mcp_time.decode(value)


@unittest.skipUnless(sys.platform=='win32' and setup.installed() is not None,'Optional pinned MCP time runtime not prepared')
class NativeTimeTests(unittest.TestCase):
    def test_actual_provider_now_conversion_and_snapshot(self):
        result=mcp_time.execute({'timezone':'Europe/Warsaw'})
        self.assertEqual(mcp_time.decode(result['url'].split('data=',1)[1])['result']['timezone'],'Europe/Warsaw')
        result=mcp_time.execute({'action':'convert','timezone':'Europe/Warsaw','target_timezone':'UTC','time':'09:30'})
        self.assertIn('dzisiejszej daty',result['text'])

    def test_cancel_closes_actual_provider_child(self):
        children=[];calls=[0]
        class Client(StdioClient):
            def __init__(self,*a,**kw):super().__init__(*a,**kw);children.append(self.process)
        def check():
            calls[0]+=1
            if calls[0]>=4:raise ToolError('tool_cancelled')
        with patch.object(mcp_time,'StdioClient',Client),self.assertRaises(ToolError) as error:mcp_time.execute({'timezone':'UTC'},check)
        self.assertEqual(error.exception.code,'tool_cancelled');self.assertTrue(children);self.assertTrue(all(child.poll() is not None for child in children))

    def test_actual_disconnect_is_failure_and_process_is_closed(self):
        children=[]
        class Client(StdioClient):
            def initialize(self,*a,**kw):
                result=super().initialize(*a,**kw);children.append(self.process);self.process.kill();self.process.wait(timeout=3);return result
        with patch.object(mcp_time,'StdioClient',Client),self.assertRaises(ToolError):mcp_time.execute({'timezone':'UTC'})
        self.assertTrue(children and all(child.poll() is not None for child in children))


class TimeAPITests(unittest.TestCase):
    def setUp(self):
        import test_native
        self.base=test_native.APITests('runTest');self.addCleanup(self.base.doCleanups);self.base.setUp()

    def test_snapshot_requires_session_and_does_not_refetch_clock(self):
        snapshot={'action':'now','captured_at':datetime.now(timezone.utc).isoformat(),'result':now_record()};value=mcp_time.encode(snapshot)
        with patch.object(mcp_time,'execute',side_effect=AssertionError('No live clock fetch')):
            response=self.base.client.get('/api/v1/integrations/mcp-time/result',params={'data':value})
        self.assertEqual(response.status_code,200);self.assertIn(snapshot['result']['datetime'],response.text);self.assertTrue(response.headers['content-type'].startswith('text/plain'))
        self.assertEqual(self.base.client.get('/api/v1/integrations/mcp-time/result',params={'data':'../bad'}).status_code,422)
        self.base.client.cookies.clear();self.assertEqual(self.base.client.get('/api/v1/integrations/mcp-time/result',params={'data':value}).status_code,401)

    def test_test_endpoint_uses_worker_rechecks_session_and_rejects_extra_secrets(self):
        from app.db import connect
        def read(name,args,scope,check):
            self.assertEqual(name,'mcp_time');self.assertTrue(scope['mcp_time_available']);check()
            return {'content_kind':'time_snapshot','text':'clock fixture','url':'/local'}
        with patch.object(tools,'bind_integrations',return_value={'mcp':True,'mcp_time_available':True}),patch.object(tools,'read',side_effect=read):
            response=self.base.post('/integrations/mcp-time/test',{'action':'now','timezone':'UTC'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.json()['available'])
        self.assertEqual(self.base.post('/integrations/mcp-time/test',{'timezone':'UTC','token':'not-accepted'}).status_code,422)
        self.assertEqual(self.base.client.post('/api/v1/integrations/mcp-time/test',json={'timezone':'UTC'},headers={'X-CSRF-Token':'bad'}).status_code,403)
        def revoke(name,args,scope,check):
            with connect() as conn:conn.execute('UPDATE sessions SET revoked_at=now()')
            check()
        with patch.object(tools,'bind_integrations',return_value={'mcp':True,'mcp_time_available':True}),patch.object(tools,'read',side_effect=revoke):self.assertEqual(self.base.post('/integrations/mcp-time/test',{'timezone':'UTC'}).status_code,401)

    def test_prepare_masks_internal_errors_and_requires_owner(self):
        from app.db import connect
        with patch.object(setup,'prepare',side_effect=OSError('PRIVATE_PATH_DETAIL')):
            response=self.base.post('/integrations/mcp-time/prepare')
        self.assertEqual(response.status_code,409);self.assertNotIn('PRIVATE_PATH',response.text)
        with connect() as conn:conn.execute("UPDATE users SET username='reader' WHERE username='owner'")
        with patch.object(setup,'prepare',side_effect=AssertionError('No install')):self.assertEqual(self.base.post('/integrations/mcp-time/prepare').status_code,403)
