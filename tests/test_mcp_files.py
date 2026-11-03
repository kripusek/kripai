"""Folder właściciela, brak zapisu, prawdziwy opcjonalny serwer i autoryzacja API."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from app import config,mcp_files,tools
from app.network import ToolError,policy
from scripts import setup_mcp_filesystem as setup
import test_native

class FilesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'notes';self.root.mkdir()
        self.data=self.base/'data';self.backups=self.base/'backups'
        for name,value in [('DATA',self.data),('BACKUPS',self.backups)]:
            patcher=patch.object(config,name,value);patcher.start();self.addCleanup(patcher.stop)
        (self.root/'guide.md').write_text('Sprawdzony dokument.',encoding='utf-8')
        self.configured=mcp_files.configure(str(self.root),'Notatki')
        self.id=self.configured['root_id']
    def code(self,code,fn,*args):
        with self.assertRaises(ToolError) as error:fn(*args)
        self.assertEqual(error.exception.code,code)
    def test_configuration_backup_disconnect_and_stale_root(self):
        self.assertNotIn('root',mcp_files.status())
        old=(self.data/'mcp-filesystem.json').read_bytes()
        mcp_files.configure(str(self.root),'Nowa nazwa')
        self.assertEqual(next(self.backups.iterdir()).read_bytes(),old)
        self.code('mcp_files_scope_changed',mcp_files.execute,'read','guide.md',self.id)
        mcp_files.disconnect();self.assertIsNone(mcp_files.settings());self.assertEqual(len(list(self.backups.iterdir())),2)
    def test_private_data_ancestors_and_drive_root_denied(self):
        self.data.mkdir(exist_ok=True);self.backups.mkdir(exist_ok=True)
        for path in [self.data,self.backups,self.base]:self.code('mcp_files_path_denied',mcp_files.root_path,str(path))
        self.code('mcp_files_configuration_invalid',mcp_files.root_path,self.root.anchor)
    def test_paths_hidden_secrets_traversal_and_size(self):
        data=mcp_files.settings()
        for value in ['../guide.md','/guide.md','C:/guide.md','.env','a/.hidden.md','guide.md:stream','a//b.md','a/./b.txt','x\n.md']:
            self.code('mcp_files_path_denied',mcp_files.local_path,data,value,True)
        (self.root/'secret.key').write_text('fixture');self.code('mcp_files_path_denied',mcp_files.local_path,data,'secret.key',True)
        (self.root/'huge.md').write_bytes(b'x'*(mcp_files.MAX_BYTES+1));self.code('mcp_files_too_large',mcp_files.local_path,data,'huge.md',True)
        (self.root/'zażółć gęślą.txt').write_text('ok',encoding='utf-8')
        self.assertTrue(mcp_files.local_path(data,'zażółć gęślą.txt',True)[0].is_file())
    def test_real_junction_cannot_escape_selected_folder(self):
        if os.name!='nt':self.skipTest('junction wymaga Windows')
        import subprocess
        outside=self.base/'outside';outside.mkdir();(outside/'file.md').write_text('private fixture')
        link=self.root/'linked'
        result=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(outside)],capture_output=True)
        if result.returncode:self.skipTest('brak możliwości utworzenia junction')
        try:self.code('mcp_files_path_denied',mcp_files.local_path,mcp_files.settings(),'linked/file.md',True)
        finally:link.rmdir()
    def test_permissions_root_snapshot_and_no_write_schema(self):
        scope=tools.bind_integrations(policy('Odczytaj guide.md oraz "zażółć gęślą.txt"',mcp=True))
        self.assertEqual(scope['mcp_files_root'],self.id);self.assertIn('zażółć gęślą.txt',scope['local_documents'])
        self.assertIn('mcp_files',[s['function']['name'] for s in tools.schemas(scope)])
        with patch.object(tools.subprocess,'Popen',side_effect=AssertionError('no spawn')):
            for current,args in [(policy('guide.md'),{'action':'read','path':'guide.md'}),(scope,{'action':'write','path':'guide.md'}),(scope,{'action':'read','path':'other.md'})]:
                with self.assertRaises(ToolError):tools.read('mcp_files',args,current,lambda:None)
        mcp_files.disconnect();self.assertNotIn('mcp_files',[s['function']['name'] for s in tools.schemas(tools.bind_integrations(policy('guide.md',mcp=True)))])
    def test_modified_or_absent_optional_runtime_is_not_available(self):
        with patch.object(setup,'installed',return_value=None):self.code('mcp_files_unavailable',mcp_files.execute,'read','guide.md',self.id)
        self.code('mcp_tool_denied',mcp_files.execute,'write','guide.md',self.id)
    def test_large_directory_denied_before_spawn(self):
        for index in range(200):(self.root/str(index)).touch()
        with patch.object(mcp_files,'StdioClient',side_effect=AssertionError('no spawn')):
            self.code('mcp_files_directory_large',mcp_files.execute,'list','',self.id)
    def test_reconfiguration_during_handshake_cancels_read(self):
        class Client:
            closed=False
            def __init__(self,check,**kwargs):self.check=check
            def initialize(self,**kwargs):
                mcp_files.configure(str(self.root),'Changed');self.check()
            def close(self):Client.closed=True
        Client.root=self.root
        with patch.object(setup,'installed',return_value=self.root),patch.object(setup,'node',return_value=Path('node')),patch.object(mcp_files,'StdioClient',Client):
            self.code('mcp_files_scope_changed',mcp_files.execute,'read','guide.md',self.id)
        self.assertTrue(Client.closed)
    def test_server_cannot_claim_write_tool_is_readonly(self):
        class Client:
            closed=False
            def __init__(self,*a,**kw):pass
            def initialize(self,**kw):return {'tools':[{'name':n,'annotations':{'readOnlyHint':False}} for n in mcp_files.READ_TOOLS]}
            def request(self,*a):raise AssertionError('must not call tool')
            def close(self):Client.closed=True
        with patch.object(setup,'installed',return_value=self.root),patch.object(setup,'node',return_value=Path('node')),patch.object(mcp_files,'StdioClient',Client):
            self.code('mcp_tool_denied',mcp_files.execute,'read','guide.md',self.id)
        self.assertTrue(Client.closed)
    def test_real_official_server_list_read_unicode_and_nested_worker(self):
        if not setup.node() or not setup.installed():self.skipTest('opcjonalny Node/serwer nieprzygotowany; test niczego nie pobiera')
        (self.root/'zażółć gęślą.txt').write_text('Prawdziwy serwer MCP: zażółć gęślą.',encoding='utf-8')
        (self.root/'.hidden.md').write_text('hidden');(self.root/'private.key').write_text('fixture')
        result=mcp_files.execute('list','',self.id)
        self.assertEqual(set(result['paths']),{'guide.md','zażółć gęślą.txt'});self.assertEqual(result['omitted_entries'],2)
        self.assertNotIn(str(self.root),json.dumps(result))
        result=mcp_files.execute('read','zażółć gęślą.txt',self.id);self.assertIn('zażółć gęślą',result['document'])
        scope=tools.bind_integrations(policy('Przeczytaj guide.md',mcp=True))
        result=tools.read('mcp_files',{'action':'read','path':'guide.md'},scope,lambda:None)
        self.assertEqual(result['document'],'Sprawdzony dokument.')
        self.assertEqual(list((self.data/'tools-tmp').iterdir()),[])
    def test_runtime_inventory_detects_tampering_and_environment_is_minimal(self):
        runtime=self.base/'runtime';runtime.mkdir();package=runtime/'node_modules';package.mkdir();(package/'a.js').write_text('original')
        marker={'version':setup.VERSION,'lock_sha256':setup.digest(setup.lock_path()),'files':setup.inventory(runtime)}
        (runtime/'.kripai-mcp-filesystem.json').write_text(json.dumps(marker));self.assertTrue(setup.verify(runtime))
        (package/'a.js').write_text('tampered');self.assertFalse(setup.verify(runtime))
        with patch.dict(os.environ,{'NPM_TOKEN':'fixture','GITHUB_TOKEN':'fixture'}),patch.object(setup,'node',return_value=Path('C:/Program Files/nodejs/node.exe')):
            env=setup.npm_environment(self.base,runtime)
        self.assertNotIn('NPM_TOKEN',env);self.assertNotIn('GITHUB_TOKEN',env);self.assertEqual(env['NPM_CONFIG_IGNORE_SCRIPTS'],'true')

class FilesAPITests(unittest.TestCase):
    def setUp(self):
        self.base=test_native.APITests('runTest');self.addCleanup(self.base.doCleanups);self.base.setUp()
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup);self.root=Path(self.folder.name)
        (self.root/'memo.md').write_text('API real MCP fixture',encoding='utf-8')
    def test_owner_config_validation_csrf_auth_and_old_source(self):
        base=self.base;route='/integrations/mcp-files/'
        response=base.post(route+'config',{'root':str(self.root),'label':'Test'});self.assertEqual(response.status_code,200,response.text)
        identity=response.json()['root_id'];self.assertEqual(base.client.get('/api/v1'+route+'config').json()['root'],str(self.root))
        self.assertEqual(base.post(route+'config',{'root':str(self.root),'command':'bad'}).status_code,422)
        self.assertEqual(base.client.post('/api/v1'+route+'disconnect',headers={'X-CSRF-Token':'bad'}).status_code,403)
        base.post(route+'config',{'root':str(self.root),'label':'Changed'})
        self.assertEqual(base.client.get('/api/v1'+route+'document',params={'root':identity,'path':'memo.md'}).status_code,404)
        with patch.object(setup,'prepare',side_effect=ValueError('private path fixture')):
            response=base.post(route+'prepare',{});self.assertEqual(response.status_code,503);self.assertNotIn('private path',response.text)
        base.client.cookies.clear();self.assertEqual(base.client.get('/api/v1'+route+'config').status_code,401)
    def test_real_server_through_authenticated_api(self):
        if not setup.node() or not setup.installed():self.skipTest('opcjonalny Node/serwer nieprzygotowany')
        base=self.base;route='/integrations/mcp-files/'
        result=base.post(route+'config',{'root':str(self.root)}).json()
        response=base.post(route+'test',{});self.assertTrue(response.json()['available'],response.text)
        response=base.client.get('/api/v1'+route+'document',params={'root':result['root_id'],'path':'memo.md'})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.text,'API real MCP fixture')
        self.assertEqual(base.post(route+'disconnect',{}).status_code,204)
