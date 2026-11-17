"""Validate six authored content strategies, not native model generation quality."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/api/src'))
from explainer.content_taxonomy import INTENT_PROFILES
from explainer.domain import Brief,StoryboardIR
from explainer.editorial import EditorialPlan
from explainer.services.editorial import prepare_presentation,require_publishable,publication_findings
from explainer.services.ingestion import analyze

results=[]
for intent in INTENT_PROFILES:
    path=ROOT/'examples/content-strategies'/f'{intent}.json'
    fixture=json.loads(path.read_text())
    brief=Brief.model_validate(fixture['brief'])
    board=StoryboardIR(title=brief.title,language=brief.language,audience=brief.audience,scenes=fixture['scenes'])
    prepare_presentation(board,brief,EditorialPlan.model_validate(fixture['editorial']))
    require_publishable(board,analyze(brief))
    results.append({'intent':intent,'title':brief.title,'subject_kind':board.editorial.strategy.subject_kind,
                    'functions':[b.function for b in board.editorial.strategy.outline],
                    'findings':publication_findings(board,analyze(brief)),
                    'fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'contract':'passed'})
report={'taxonomy_version':'1.0','fixture_kind':'fixed authored editorial examples, not model responses',
        'results':results,'native_inference':False,'tts_or_full_listening':False,
        'limits':['Structural coverage is not semantic quality certification.','Real native outputs for all six purposes require deployment acceptance.']}
(ROOT/'docs/verification-taxonomy.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Six authored editorial strategy contracts passed')
