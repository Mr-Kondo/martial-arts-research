#!/usr/bin/env python3
"""Prepare frozen, private inputs for the artifact study; does not call a model."""
import argparse
import json
from pathlib import Path

from evaluate_maintenance import digest
from evaluate_retrieval import ROOT, corpus, freeze


def validate(data, evidence):
    cases = data.get('cases') if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError('nonempty cases list required')
    ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError('case must be an object')
        if any(not isinstance(case.get(k), str) or not case[k].strip()
               for k in ('id', 'request', 'observations')):
            raise ValueError('case text missing')
        if not isinstance(case.get('draft'), str):
            raise ValueError('draft must be text (empty for new artifacts)')
        if case['id'] in ids:
            raise ValueError('duplicate case ID')
        ids.add(case['id'])
        if case.get('split') not in ('development', 'confirmation') or case.get('scene') not in ('update', 'normal'):
            raise ValueError('invalid case split or scene')
        for name, count in [('required', 3), ('forbidden', 2)]:
            if (not isinstance(case.get(name), list) or len(case[name]) != count
                    or any(not isinstance(v, str) or not v.strip() for v in case[name])):
                raise ValueError('invalid case oracle')
        if (not isinstance(case.get('sources'), list) or not case['sources']
                or any(not isinstance(p, str) or p not in evidence for p in case['sources'])):
            raise ValueError('unavailable canonical case source')
    return cases


def prepare(cases_path, out):
    data = json.loads(cases_path.read_text(encoding='utf-8'))
    validate(data, corpus())
    original = ROOT/'evals/fixtures/wikiskill-retrieval'
    manifest = freeze(original, out)
    entry = (ROOT/'evals/fixtures/wikiskill-artifacts/lazy-entry-v2.md').read_text(encoding='utf-8')
    system = (out/'A-system.md').read_text(encoding='utf-8')+'\n'+entry
    (out/'B3-system.md').write_text(system, encoding='utf-8')
    manifest['systems']['B3'] = digest(system)
    manifest['candidate_version'] = 'B3-entry-v2; B1/B2 unchanged'
    manifest['cases_sha256'] = digest(cases_path.read_text(encoding='utf-8'))
    (out/'cases-all.json').write_text(cases_path.read_text(encoding='utf-8'), encoding='utf-8')
    (out/'frozen.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT/'evals/fixtures/wikiskill-artifacts/cases.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.cases.resolve(), args.out.resolve())
    print('frozen inputs prepared; no model called')
