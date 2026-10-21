import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from capcut_mcp import paths, edits, ir, preview
from capcut_mcp.draft import Draft, DraftError


class MacPathsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_bundle_plist_and_resources(self):
        bundle = self.root/'CapCut.app'
        resource = bundle/'Contents/Resources/Font/SystemFont/NotoSans-Regular.ttf'
        resource.parent.mkdir(parents=True)
        resource.write_bytes(b'font fixture')
        with (bundle/'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleShortVersionString':'test-version'}, stream)
        with patch.dict('os.environ', {paths.ENV_APP:str(bundle)}):
            self.assertEqual(paths.installed_version(),'test-version')
            self.assertEqual(paths.find_bundled_font(),str(resource))

    def test_explicit_root_verified_not_guessed(self):
        (self.root/paths.META_FILE).write_text('{}')
        with patch.dict('os.environ',{paths.ENV_DRAFT_ROOT:str(self.root)}):
            self.assertEqual(paths.find_draft_root(),self.root)
        with self.assertRaises(FileNotFoundError):paths.find_draft_root(str(self.root/'missing'))

    def test_multiple_stores_refuse_selection(self):
        second=self.root/'other';second.mkdir()
        for folder in [self.root,second]:(folder/paths.META_FILE).write_text('{}')
        with patch.dict('os.environ',{},clear=True),patch.object(paths,'_candidate_roots',return_value=iter([self.root,second])):
            with self.assertRaises(FileNotFoundError):paths.find_draft_root()

    def test_native_processes_with_spaces_and_helpers(self):
        listing='  1 /sbin/launchd\n 42 /Applications/CapCut.app/Contents/MacOS/CapCut\n 43 /Applications/CapCut.app/Contents/Frameworks/CapCut Helper\n 44 /bin/bash\n'
        with patch.object(paths.sys,'platform','darwin'),patch.object(paths.subprocess,'run',return_value=subprocess.CompletedProcess([],0,listing,'')):
            self.assertEqual(paths.running_pids(),[42,43])

    def test_closed_processes(self):
        with patch.object(paths.sys,'platform','darwin'),patch.object(paths.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'1 /sbin/launchd\n2 /bin/bash','')):
            self.assertEqual(paths.running_pids(),[])

    def test_process_failure_and_empty_result_refuse(self):
        with patch.object(paths.sys,'platform','darwin'):
            with patch.object(paths.subprocess,'run',side_effect=OSError('denied')):
                with self.assertRaises(paths.ProcessInspectionError):paths.running_pids()
            with patch.object(paths.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')):
                with self.assertRaises(paths.ProcessInspectionError):paths.running_pids()
            with patch.object(paths.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'1 /bin/bash\nmalformed row','')):
                with self.assertRaises(paths.ProcessInspectionError):paths.running_pids()

    def test_non_mac_refuses_process_state(self):
        with patch.object(paths.sys,'platform','linux'):
            with self.assertRaises(paths.ProcessInspectionError):paths.running_pids()

    def test_index_paths_and_foreign_media(self):
        folder=self.root/'sample';folder.mkdir();(folder/'draft_content.json').write_text('{}')
        entries=[{'draft_name':'Mac sample','draft_fold_path':'sample'},
                 {'draft_name':'PC sample','draft_fold_path':'D:/CapCut/example'},
                 {'draft_name':'Empty','draft_fold_path':''}]
        (self.root/paths.META_FILE).write_text(json.dumps({'all_draft_store':entries}))
        projects={p['name']:p for p in paths.list_projects(self.root)}
        self.assertTrue(projects['Mac sample']['available'])
        self.assertFalse(projects['PC sample']['available'])
        self.assertFalse(projects['Empty']['available'])

    def test_binary_explicit_and_homebrew_fallback(self):
        with patch.dict('os.environ',{'CAPCUT_MCP_FFMPEG':'/opt/custom/ffmpeg'}),patch.object(paths,'_is_file',return_value=True),patch.object(paths.os,'access',return_value=True):
            # The Windows test host does not use POSIX absolute paths.
            with patch.object(paths.Path,'is_absolute',return_value=True):
                self.assertEqual(paths.binary('ffmpeg'),str(Path('/opt/custom/ffmpeg')))
        with patch.dict('os.environ',{},clear=True),patch.object(paths.shutil,'which',return_value=None),patch.object(paths,'_is_file',side_effect=lambda p:str(p).replace('\\','/')=='/opt/homebrew/bin/ffmpeg'),patch.object(paths.os,'access',return_value=True):
            self.assertEqual(paths.binary('ffmpeg'),str(Path('/opt/homebrew/bin/ffmpeg')))


class MacDraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.file=self.root/'draft_content.json'
        self.data={'version':360000,'tracks':[],'materials':{},'duration':0}
        self.original=json.dumps(self.data).encode();self.file.write_bytes(self.original)
        self.draft=Draft.open(str(self.root))

    def test_save_and_backup_only_scratch_project(self):
        self.draft.data['name']='changed'
        with patch.object(paths,'running_pids',return_value=[]):result=self.draft.save()
        self.assertEqual(Path(result['backup']).read_bytes(),self.original)
        self.assertEqual(json.loads(self.file.read_text())['name'],'changed')

    def test_running_and_unverified_processes_block_write(self):
        for answer in [[123],paths.ProcessInspectionError('denied')]:
            with patch.object(paths,'running_pids',**({'side_effect':answer} if isinstance(answer,Exception) else {'return_value':answer})):
                with self.assertRaises((DraftError,paths.ProcessInspectionError)):self.draft.save()
            self.assertEqual(self.file.read_bytes(),self.original)

    def test_force_and_no_backup_are_rejected(self):
        with self.assertRaises(DraftError):self.draft.save(force=True)
        with self.assertRaises(DraftError):self.draft.save(backup=False)
        self.assertEqual(self.file.read_bytes(),self.original)

    def test_concurrent_changes_and_app_start_block(self):
        self.file.write_text('{"external":true}')
        with patch.object(paths,'running_pids',return_value=[]):
            with self.assertRaises(DraftError):self.draft.save()
        self.assertEqual(self.file.read_text(),'{"external":true}')
        self.file.write_bytes(self.original)
        with patch.object(paths,'running_pids',side_effect=[[],[123]]):
            with self.assertRaises(DraftError):self.draft.save()
        self.assertEqual(self.file.read_bytes(),self.original)
        self.assertFalse(self.file.with_suffix('.json.mcp-tmp').exists())

    def test_text_add_then_delete_does_not_write(self):
        result=edits.add_text(self.draft.data,'MCP TEST',start=0,duration=2)
        self.assertEqual(ir.build(self.draft.data,'sample')['tracks'][0]['clips'][0]['text'],'MCP TEST')
        edits.delete_clip(self.draft.data,result['clip_id'])
        self.assertEqual(self.file.read_bytes(),self.original)

    def test_no_denoise_model_does_not_enable_missing_resource(self):
        with patch.object(paths,'find_denoise_model',return_value=None):
            data={'materials':{}}
            edits._companions(data,'video',1_000_000)
            self.assertFalse(data['materials']['realtime_denoises'][0]['is_denoise'])

    def test_text_preview_fails_without_font(self):
        edits.add_text(self.draft.data,'MCP TEST',start=0,duration=2)
        with patch.object(paths,'binary',return_value='ffmpeg'),patch.object(preview,'_default_font',return_value=None):
            with self.assertRaises(preview.PreviewError):preview.build_command(ir.build(self.draft.data,'sample'),self.root/'test.mp4')


if __name__=='__main__':unittest.main()
