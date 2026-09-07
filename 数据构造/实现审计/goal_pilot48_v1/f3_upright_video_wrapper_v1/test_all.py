import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .runtime import VideoContext
class Tests(unittest.TestCase):
    def case(self,start_error=False,started=True):
        calls=[]
        def start(path):
            calls.append('video_start')
            if start_error:raise ValueError('encoder start')
            Path(path).parent.mkdir(parents=True,exist_ok=True)
            return {'started':started,'path':str(path),'video_fps':25,'sample_stride_steps':10}
        scene=SimpleNamespace(start_development_video_capture=start)
        class Inner:
            cleanup_receipt={'development_video_receipt':{'fake_CPU':True}}
            def __enter__(self):calls.append('settled_scene_enter');return SimpleNamespace(scene=scene)
            def __exit__(self,*a):calls.append('original_finalize_cleanup')
        with tempfile.TemporaryDirectory(dir='/nfs_share/lijunhui/Robotwin2/tmp') as directory:
            ctx=VideoContext(Inner(),Path(directory)/'video/test.mp4')
            try:
                with ctx:calls.append('standing_and_task')
            except ValueError:pass
            except RuntimeError:pass
        return calls
    def test_starts_before_standing_or_task_and_uses_original_cleanup(self):
        self.assertEqual(self.case(),['settled_scene_enter','video_start','standing_and_task','original_finalize_cleanup'])
    def test_encoder_start_failure_still_cleans_without_action(self):
        self.assertEqual(self.case(start_error=True),['settled_scene_enter','video_start','original_finalize_cleanup'])
    def test_false_start_does_not_allow_task(self):
        self.assertEqual(self.case(started=False),['settled_scene_enter','video_start','original_finalize_cleanup'])
    def test_no_manifest_can_silently_disable_video(self):
        from .runtime import run
        with self.assertRaises(ValueError):run({'video_capture_required':False},meter=None)
if __name__=='__main__':unittest.main()
