"""Real integration: prompt and source pipeline, narrated MP4 and incremental audio reuse.

Requires ffmpeg, Node dependencies and Chrome. Uses eSpeak if available.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from explainer.config import Settings
from explainer.db import Database, encode
from explainer.api import insert_revision
from explainer.domain import Brief, StoryboardIR
from explainer.storage import Storage
from explainer.worker import run_once

parser = argparse.ArgumentParser()
parser.add_argument('--source', action='store_true')
parser.add_argument('--chinese', action='store_true')
parser.add_argument('--output', default='.media-smoke')
args = parser.parse_args()
settings = Settings(data_dir=ROOT / args.output, api_token='media-test-key-not-production-123456',
                    chrome_executable=os.getenv('CHROME_EXECUTABLE','')).prepare()
db = Database(settings.data_dir)
project_id = 'sample_project'
db.execute('INSERT OR IGNORE INTO projects VALUES(?,?,?,?)',(project_id,'local','Sample',time.time()))
brief = Brief(title='Understanding an API', prompt='Explain how a request becomes a response.',
              language='en-US', target_seconds=20, voice='auto', mode='automatic')
board = StoryboardIR(title=brief.title,language=brief.language,accent='blue',audience='general',scenes=[
    {'id':'start','type':'title','title':'A small request. A useful response.',
     'narration':'An API is a defined interface between software systems.',
     'bullets':['A clear contract','A shared language'],'claim_ids':['c_prompt'],'verification':'user_provided','duration':5},
    {'id':'flow','type':'flow','title':'From request to response',
     'narration':'A client sends a request. The service processes it and returns a response.',
     'bullets':['Client','Request','Service','Response'],'claim_ids':['c_prompt'],'verification':'user_provided','duration':8},
    {'id':'end','type':'summary','title':'Keep the contract clear.',
     'narration':'Inputs, outputs, and errors form a contract that both sides can understand.',
     'bullets':['Inputs','Outputs','Errors'],'claim_ids':['c_prompt'],'verification':'user_provided','duration':7},
])
if args.chinese:
    brief.title='把内容变成讲解视频'
    brief.language='zh-CN'
    board.title=brief.title
    board.language=brief.language
    translations=[
        ('从内容出发，让理解发生。','输入一个想法或一份源码，开始创作讲解视频。',['一个想法','一份源码']),
        ('从输入到讲解视频','系统梳理内容，编排分镜，生成旁白和动画，再输出视频。',['理解内容','编排分镜','赋予声音','生成视频']),
        ('让复杂，一目了然。','脚本、字幕和工程都可以继续编辑，每次修改保留独立版本。',['可编辑的工程','可追溯的版本','可导出的视频'])]
    for scene,(title,narration,bullets) in zip(board.scenes,translations):
        scene.title,scene.narration,scene.bullets=title,narration,bullets
if args.source:
    from explainer.services.ingestion import read_archive
    data=(ROOT/'examples/source-demo.zip').read_bytes()
    manifest=read_archive(data,settings)
    asset=Storage(settings,db).put('local',data,'source','source.zip','application/zip')
    db.execute('INSERT OR REPLACE INTO inputs VALUES(?,?,?,?,?,?)',('sample_input','local',project_id,asset['id'],encode(manifest),time.time()))
    brief=Brief(title='Source project walkthrough',input_id='sample_input',language='en-US',target_seconds=40,voice='none')
    board=None
result=insert_revision(db,settings,'local',project_id,brief,storyboard=board)
run_once(settings,db,job_id=result['job_id'])
job=db.one('SELECT * FROM jobs WHERE id=?',(result['job_id'],))
assert job['state'] in {'SUCCEEDED','PARTIAL'},job
outputs=db.all('SELECT * FROM outputs WHERE revision_id=?',(result['revision_id'],))
storage=Storage(settings,db)
directory=settings.data_dir/'deliverables'
directory.mkdir(exist_ok=True)
for out in outputs:
    a,path=storage.get('local',out['asset_id'])
    if out['role'] in {'video','package','script','subtitles','quality','cover'}:
        (directory/a['filename']).write_bytes(path.read_bytes())
print(json.dumps({'state':job['state'],'revision_id':result['revision_id'],'directory':str(directory),'outputs':outputs},indent=2))

