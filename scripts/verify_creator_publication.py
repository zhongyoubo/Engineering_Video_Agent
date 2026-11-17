"""Render ONLY this fixed repository-authored creator fixture, never external/generated code.

Exercise native-project wrapping and compatibility rendering, plus separate 4K thumbnail.
No Agent inference/TTS/listening acceptance. Large rendered evidence stays in .verify-creator.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.domain import Brief, Scene, StoryboardIR
from explainer.services.editorial import prepare_presentation, require_publishable
from explainer.services.ingestion import analyze
from explainer.services.engineering.workspace import Workspace
from explainer.services.engineering.contracts import SourceEdit
from explainer.services.engineering.tools import inspect_frame
from explainer.services.process import Runner
from explainer.services.quality import inspect_video


def main():
    out = ROOT / '.verify-creator'
    out.mkdir(exist_ok=True)
    media = out / 'media'
    media.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf', media / 'noto.otf')
    brief = Brief(title='配音怎么选？', prompt='用自己的文稿检查音色和表达', quality_profile='draft', voice='none')
    board = StoryboardIR(title=brief.title, language='zh-CN', audience='general', total_frames=180, scenes=[
        Scene(id='opening', type='title', title=brief.title, narration='怎样判断配音是否适合？', start_frame=0, frames=60, duration=2),
        Scene(id='example', type='cards', title='同一句话，检查两个维度', narration='检查音色和表达', start_frame=60, frames=60, duration=2,
              bullets=['音色是否合适', '表达是否到位'], disclosures=[{'text': '方法示例', 'end_seconds': 1}]),
        Scene(id='closing', type='summary', title='先试听，再决定', narration='拿自己的文稿试听', message='拿自己的文稿试听', start_frame=120, frames=60, duration=2),
    ])
    prepare_presentation(board, brief)
    board.cover.subtitle = '拿自己的文稿试听'
    require_publishable(board, analyze(brief))
    props = board.model_dump()
    w = Workspace(out / 'engineering')
    w.prepare(props, media)
    source = (ROOT / 'examples/creator-publication/Video.tsx').read_text()
    w.edit([SourceEdit(path='src/Video.tsx', content=source)])
    link = w.project / 'node_modules'
    if not link.exists():
        link.symlink_to(ROOT / 'node_modules', target_is_directory=True)
    fingerprint = w.fingerprint()
    runner = Runner()
    receipts = {}
    for action in ['preview', 'final']:
        target = out / action
        target.mkdir(exist_ok=True)
        assert w.state['files'] == {'src/Video.tsx': source}
        runner.run(['node', ROOT / 'packages/engineering-template/render.mjs', w.project, action, target], timeout=600, env=os.environ.copy())
        receipts[action] = json.loads((target / 'result.json').read_text())
        assert receipts[action]['ok'] and w.fingerprint() == fingerprint
    frames = receipts['preview']['frames']
    assert any(f['frame'] == 0 and f.get('kind') != 'thumbnail' for f in frames)
    assert any(f['name'] == 'cover.png' and f.get('kind') == 'thumbnail' for f in frames)
    for frame in frames:
        inspect_frame(out / 'preview' / frame['name'])
    engineering_media = inspect_video(out / 'final/video.mp4', runner, 180)
    compatibility = out / 'compatibility'
    compatibility.mkdir(exist_ok=True)
    shutil.copytree(media, compatibility / 'public', dirs_exist_ok=True)
    (compatibility / 'props.json').write_text(json.dumps(props, ensure_ascii=False))
    runner.run(['node', ROOT / 'packages/video/render.mjs', compatibility], timeout=600, env=os.environ.copy())
    compatibility_media = inspect_video(compatibility / 'video.mp4', runner, 180)
    inspect_frame(compatibility / 'cover.png')
    # Independent, vector-scaled 4K thumbnail through the same registered composition.
    runner.run(['node', ROOT / 'scripts/verify_creator_thumbnail.mjs', compatibility], timeout=120, env=os.environ.copy())
    inspect_frame(compatibility / 'cover-4k.png', 3840, 2160)
    compatibility_sources = [ROOT / 'packages/video/render.mjs', *sorted((ROOT / 'packages/video/src').glob('*')), ROOT / 'packages/engineering-template/src/presentation.tsx']
    compatibility_hash = hashlib.sha256()
    for path in compatibility_sources:
        compatibility_hash.update(str(path.relative_to(ROOT)).encode())
        compatibility_hash.update(path.read_bytes())
    result = {
        'fixture': 'fixed repository-authored silent draft; no native inference or TTS',
        'source_hash': fingerprint,
        'compatibility_source_hash': compatibility_hash.hexdigest(),
        'engineering_media': engineering_media,
        'compatibility_media': compatibility_media,
        'review_samples': frames,
        'independent_thumbnail_composition': 'PublicationThumbnail',
        'thumbnail_4k': {'width': 3840, 'height': 2160, 'sha256': hashlib.sha256((compatibility / 'cover-4k.png').read_bytes()).hexdigest()},
        'full_human_playback_and_listening': False,
    }
    (ROOT / 'docs/verification-creator.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
