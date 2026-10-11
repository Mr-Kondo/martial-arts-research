"""Bounded audits and deterministic Markdown; called after schema validation."""
import ast
import datetime as dt
from fractions import Fraction
import hashlib
import html
from http.client import HTTPException
import json
import re
import unicodedata
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

# Base dimensions: mass, length, time. Unknown units are never dimensionless.
UNITS = {
    '1': ('1', (0, 0, 0)), 'kg': ('1', (1, 0, 0)), 'g': ('0.001', (1, 0, 0)),
    't': ('1000', (1, 0, 0)), 'm': ('1', (0, 1, 0)), 'cm': ('0.01', (0, 1, 0)),
    'mm': ('0.001', (0, 1, 0)), 'km': ('1000', (0, 1, 0)), 's': ('1', (0, 0, 1)),
    'ms': ('0.001', (0, 0, 1)), 'min': ('60', (0, 0, 1)), 'h': ('3600', (0, 0, 1)),
    'm/s': ('1', (0, 1, -1)), 'km/h': ('5/18', (0, 1, -1)),
    'N': ('1', (1, 1, -2)), 'J': ('1', (1, 2, -2))}
NUMBER = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?'


class Unsupported(ValueError):
    """An input outside the deliberately small executable rule set."""


def numeric(value):
    if not isinstance(value, str) or len(value) > 40 or re.fullmatch(NUMBER, value) is None:
        raise Unsupported('概数・範囲・長い数値は自動計算対象外')
    if 'e' in value.lower() and abs(int(value.lower().split('e')[1])) > 12:
        raise Unsupported('指数の絶対値は12以下')
    return Fraction(value)


def unit(value):
    if value not in UNITS:
        raise Unsupported('未対応または不明の単位: ' + str(value))
    scale, dimensions = UNITS[value]
    return Fraction(scale), dimensions


def calculate(measurement):
    calculation = measurement['calculation']
    formula = calculation['formula']
    if len(formula) > 512:
        raise Unsupported('式は512文字以下')
    try:
        tree = ast.parse(formula, mode='eval')
    except (SyntaxError, ValueError, RecursionError) as error:
        raise Unsupported('未対応の式') from error
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise Unsupported('式は64ノード以下')
    values = {}
    for entry in calculation['inputs']:
        name = entry['name']
        if not name.isidentifier():
            raise Unsupported('入力名は識別子が必要')
        if name in values:
            raise ValueError('計算入力名の重複')
        scale, dimensions = unit(entry['unit'])
        values[name] = (numeric(entry['value']) * scale, dimensions)

    def evaluate(node):
        if isinstance(node, ast.Name):
            if node.id not in values:
                raise Unsupported('入力名に対応しない式の語句: ' + node.id)
            return values[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return numeric(ast.get_source_segment(formula, node)), (0, 0, 0)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value, dimensions = evaluate(node.operand)
            return (-value if isinstance(node.op, ast.USub) else value), dimensions
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, ld = evaluate(node.left)
            right, rd = evaluate(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if ld != rd:
                    raise ValueError('加減算する量の次元が不一致')
                return (left + right if isinstance(node.op, ast.Add) else left - right), ld
            if isinstance(node.op, ast.Mult):
                return left * right, tuple(a + b for a, b in zip(ld, rd))
            return left / right, tuple(a - b for a, b in zip(ld, rd))
        raise Unsupported('式は入力名・数値・括弧・四則演算だけ。呼出し・属性・累乗は実行しない')

    result, dimensions = evaluate(tree.body)
    scale, expected_dimensions = unit(measurement['unit'])
    if dimensions != expected_dimensions:
        raise ValueError('計算結果と出力単位の次元が不一致')
    result /= scale
    if 'decimal_places' in calculation:
        if calculation['rounding'] != 'ROUND_HALF_UP':
            raise Unsupported('decimal_places指定時のroundingはROUND_HALF_UPのみ')
        factor = 10 ** calculation['decimal_places']
        value = abs(result) * factor
        rounded = (2 * value.numerator + value.denominator) // (2 * value.denominator)
        result = Fraction(rounded if result >= 0 else -rounded, factor)
    elif calculation['rounding'] not in ('なし', '丸めなし', 'none'):
        raise Unsupported('丸め方を実行可能な形式で指定する必要')
    return result, numeric(measurement['original_value'])


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def doi_key(value):
    if not isinstance(value, str) or not value:
        return None
    value = value.strip()
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value, flags=re.I)
    if len(value) > 200 or re.fullmatch(r'10\.[0-9]{4,9}/[^\s\x00-\x1f\x7f]+', value) is None:
        return None
    return value.casefold()


def safe_url(value):
    if not isinstance(value, str) or re.search(r'[\s\x00-\x1f\x7f]', value):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        parts.port
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))
    except ValueError:
        return None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def fetch_crossref(doi):
    endpoint = 'https://api.crossref.org/works/' + quote(doi, safe='')
    request = Request(endpoint, headers={'Accept': 'application/json', 'User-Agent': 'martial-arts-research DOI-audit'})
    with build_opener(NoRedirect()).open(request, timeout=5) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Crossref応答上限1 MiB超過')
    payload = json.loads(raw.decode('utf-8'))
    metadata = payload.get('message') if isinstance(payload, dict) else None
    if not isinstance(metadata, dict) or doi_key(metadata.get('DOI')) != doi:
        raise ValueError('Crossref応答のDOI不一致または不正形式')
    json.dumps(metadata, ensure_ascii=False, allow_nan=False).encode('utf-8')
    for key in ('published', 'published-print', 'published-online', 'issued'):
        dates = metadata.get(key)
        if dates is not None and (not isinstance(dates, dict) or not isinstance(dates.get('date-parts', []), list)):
            raise ValueError('Crossref日付の不正形式')
    return metadata, {'url': endpoint, 'retrieved_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                      'sha256': hashlib.sha256(raw).hexdigest()}


def audit_record(record, snapshot, validation, online=False):
    result = dict(validation)
    result['record_sha256'] = hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                                       separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    checks = result['audit_checks'] = []

    def add(code, status, at, message, **details):
        checks.append({'code': code, 'status': status, 'at': at, 'message': message, 'details': details})

    if validation['record_integrity'] != 'pass':
        result['audit_status'] = 'blocked'
        return result
    for warning in validation['warnings']:
        add(warning['code'], 'not_checked', warning['at'], warning['message'])
    spans = {entry['id']: entry for entry in snapshot['spans']} if snapshot else {}
    files = {entry['id']: entry for entry in snapshot['files']} if snapshot else {}
    sources = {entry['id']: entry for entry in record['sources']}
    identities, cache = {}, {}
    for sid, source in sources.items():
        at = 'sources.' + sid
        bibliography = source['bibliography']
        doi = doi_key(bibliography['doi']) or doi_key(bibliography['url'])
        url = safe_url(bibliography['url'])
        if bibliography['doi'] and not doi:
            add('DOI_FORMAT', 'review_required', at, 'DOIの形式を確認。資料の不存在とは判定しない')
        if bibliography['url'] and not url:
            add('URL_FORMAT', 'review_required', at, '安全なHTTP(S)リンクとして出力できないURL')
        keys = [('doi', doi), ('url', url)]
        if source['file_id'] in files:
            keys.append(('body_hash', files[source['file_id']]['sha256']))
        for kind, key in keys:
            if not key:
                continue
            previous = identities.setdefault((kind, key), sid)
            if previous != sid:
                add('DUPLICATE_SOURCE', 'review_required', at, '同一の識別情報。独立した裏付けとして重複集計しない',
                    other_source=previous, identity_kind=kind, identity=key)
        cited_sources = source.get('source_context', {}).get('cited_sources') or []
        for cited in [cited_sources] if isinstance(cited_sources, str) else cited_sources:
            if cited in sources and cited != sid:
                add('COMMON_ORIGIN', 'review_required', at, '別の採用資料を引用元として申告。根拠の独立性を確認', cited_source=cited)
        if not doi:
            add('BIBLIOGRAPHY', 'not_checked', at, '照合可能なDOIなし。書誌の実在・正確性は未検証')
            continue
        if not online:
            add('BIBLIOGRAPHY', 'not_checked', at, 'オンライン照合は未実施', doi=doi)
            continue
        if doi not in cache:
            if len(cache) >= 10:
                add('BIBLIOGRAPHY', 'not_checked', at, 'オンライン照合は1実行10 DOIまで', doi=doi)
                continue
            try:
                cache[doi] = fetch_crossref(doi)
            except (OSError, ValueError, TypeError, AttributeError, RecursionError, HTTPException) as error:
                cache[doi] = str(error)
        fetched = cache[doi]
        if isinstance(fetched, str):
            add('BIBLIOGRAPHY', 'not_checked', at, 'Crossref照合不能。未登録・通信失敗を虚偽扱いしない', doi=doi, reason=fetched)
            continue
        metadata, acquisition = fetched
        add('DOI_REGISTERED', 'checked', at, 'CrossrefのDOIと一致。内容の真偽は未判定', doi=doi, acquisition=acquisition)
        title = metadata.get('title')
        titles = title if isinstance(title, list) else []
        years = set()
        for key in ('published', 'published-print', 'published-online', 'issued'):
            dates = metadata.get(key)
            if isinstance(dates, dict):
                for parts in dates.get('date-parts', []):
                    if isinstance(parts, list) and parts and type(parts[0]) is int:
                        years.add(str(parts[0]))
        authors = metadata.get('author', [])
        author_names = [' '.join(a.get(k, '') for k in ('given', 'family')).strip()
                        for a in authors if isinstance(a, dict) and all(isinstance(a.get(k, ''), str) for k in ('given', 'family'))] if isinstance(authors, list) else []
        comparisons = {'title': [t for t in titles if isinstance(t, str)], 'year': sorted(years),
                       'author': ['; '.join(author_names)] if author_names else []}
        for field, observed in comparisons.items():
            declared = bibliography[field]
            if not declared or not observed:
                add('METADATA_' + field.upper(), 'not_checked', at, '書誌項目を照合できない', field=field)
            else:
                matches = normalized(declared) in {normalized(value) for value in observed}
                add('METADATA_' + field.upper(), 'checked' if matches else 'review_required', at,
                    '登録情報と一致' if matches else '登録情報との表記・版の違いを確認。虚偽とは断定しない',
                    declared=declared, observed=observed)
        relation = metadata.get('relation', {})
        if metadata.get('update-to') or (isinstance(relation, dict) and any('retract' in key or 'update' in key or 'correct' in key for key in relation)):
            add('PUBLICATION_UPDATE', 'review_required', at, '更新・撤回関連の登録情報あり。関係と該当主張を原資料で確認')

    for finding in record['findings']:
        at = 'findings.' + finding['id']
        evidence = [e for a in finding['assessments'] for e in a['evidence']]
        for i, entry in enumerate(evidence):
            ea = at + '.evidence[' + str(i) + ']'
            if entry.get('quote') and entry['span_id'] in spans:
                add('QUOTE_MATCH', 'checked', ea, '根拠引用は保存した範囲と逐語一致。主張への実質的支持は未判定')
            else:
                add('QUOTE_UNCHECKED', 'not_checked', ea, '保存範囲に対応した根拠の逐語引用なし')
        measurements = finding.get('measurements', [])
        known_values = {}
        for i, measurement in enumerate(measurements):
            ma = at + '.measurements[' + str(i) + ']'
            if measurement['calculation'] is not None:
                try:
                    computed, declared = calculate(measurement)
                    add('CALCULATION', 'checked' if computed == declared else 'error', ma,
                        '指定した入力・単位・式・丸めで一致' if computed == declared else '指定した入力・単位・式・丸めで計算結果が不一致',
                        computed=str(computed), declared=measurement['original_value'], unit=measurement['unit'])
                except Unsupported as error:
                    add('CALCULATION', 'not_checked', ma, str(error))
                except (ValueError, ZeroDivisionError, OverflowError) as error:
                    add('CALCULATION', 'error', ma, str(error))
                add('CALCULATION_INPUT_VALIDITY', 'not_checked', ma, '入力値の来歴・仮定と式の物理的妥当性は別途確認')
            else:
                quoted = [e['quote'] for e in evidence if e['source_id'] == measurement['source_id']
                          and e['locator'] == measurement['source_locator'] and e.get('quote') and e['span_id'] in spans]
                if quoted:
                    present = any(re.search(r'(?<![0-9.+-])' + re.escape(measurement['original_value']) + r'(?![0-9.eE])', q) for q in quoted)
                    add('SOURCE_VALUE_TOKEN', 'checked' if present else 'review_required', ma,
                        '値の表記が逐語引用に存在。対象・属性への対応は未検証' if present else '値の表記が対応する逐語引用に見つからない。転記・表記差を確認')
                else:
                    add('SOURCE_VALUE', 'not_checked', ma, '数値と照合できる保存済み逐語引用なし')
            if measurement['conditions'] is not None:
                try:
                    scale, dimensions = unit(measurement['unit'])
                    value = numeric(measurement['original_value']) * scale
                    key = (measurement['equipment_id'], measurement['quantity'], measurement['conditions'], measurement['value_kind'], dimensions)
                    previous = known_values.setdefault(key, value)
                    if previous != value:
                        add('VALUE_CONFLICT', 'review_required', ma, '同装備・量・申告条件・値種別の数値が不一致。時点・版も確認', values=[str(previous), str(value)])
                except Unsupported:
                    pass
        if record['context']['task'] == 'compare' and len(measurements) > 1:
            groups = {}
            for measurement in measurements:
                groups.setdefault(measurement['quantity'], []).append(measurement)
            for quantity, group in sorted(groups.items()):
                if len(group) < 2:
                    continue
                conditions = {m['conditions'] for m in group}
                kinds = {m['value_kind'] for m in group}
                try:
                    dimensions = {unit(m['unit'])[1] for m in group}
                    if len(dimensions) != 1:
                        add('COMPARISON_UNITS', 'review_required', at, '同じ量として比較した単位の次元が不一致', quantity=quantity)
                except Unsupported:
                    add('COMPARISON_UNITS', 'not_checked', at, '比較する量に未対応または不明の単位あり', quantity=quantity)
                if None in conditions or len(conditions) != 1 or len(kinds) != 1:
                    add('COMPARISON_CONDITIONS', 'review_required', at, '比較する量の条件が不明・不一致、または公称／試験／推定を混在', quantity=quantity)
                else:
                    add('COMPARISON_CONDITIONS', 'checked', at, '申告条件と値種別が一致。型式・時点・測定方法の実質的同等性は未判定', quantity=quantity)
        inference = finding.get('inference_context')
        if inference is None:
            add('INFERENCE', 'not_checked', at, '構造化した推論種別なし。自然文の論理は未検証')
        else:
            kind, basis = inference['claim_kind'], inference['basis_kind']
            if kind == 'causal':
                add('CAUSAL_IDENTIFICATION', 'review_required', at, '因果を申告。交絡・識別方法と資料の支持を確認',
                    basis=basis, confounders=inference['confounders'], identification=inference['identification'])
            elif kind == 'effectiveness' and basis in ('prediction', 'normative', 'declared', 'model', 'association'):
                add('INFERENCE_LEAP', 'review_required', at, '予測・規範・公称・モデル・関連から実行成功への飛躍を確認', basis=basis)
            elif kind == 'generalization':
                add('GENERALIZATION', 'review_required', at, '対象集団・課題・環境を超える一般化の根拠を確認', basis=basis)
            else:
                add('INFERENCE', 'not_checked', at, '既知の飛躍規則には該当しない。論理の正しさは未検証', basis=basis)
    add('SOURCE_TRUTH', 'not_checked', 'record', '資料そのものの真偽・引用の意味・分類申告の正しさ・歴史と因果は未判定')
    statuses = {entry['status'] for entry in checks}
    result['audit_status'] = 'error' if 'error' in statuses else 'review_required' if statuses & {'review_required', 'not_checked'} else 'checked'
    return result


def literal(value):
    if value is None:
        return '未記載'
    value = html.escape(str(value), quote=False)
    value = re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', value)
    value = value.replace('\r', '&#13;').replace('\n', '<br>').replace('\t', '&#9;')
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', lambda m: '&#' + str(ord(m[0])) + ';', value)


LABELS = {
    'mode': '考証対象', 'task': '作業', 'question': '問い', 'scope': '範囲', 'conditions': '条件',
    'assumptions': '仮定', 'checked_on': '確認日', 'requested_extensions': '指定した拡張',
    'fiction_context': '作品の文脈', 'story_point': '物語時点', 'target': '検討対象', 'type': '種別',
    'text': '内容', 'span_id': '保存範囲ID', 'quote': '逐語引用', 'domain': '対象領域',
    'facts': '資料の記載・事実として記録した内容', 'analysis': '分析',
    'alternative_interpretations': '代替解釈', 'limitations': '限界', 'revision': '修正案',
    'evidence': '根拠', 'source_id': '出典ID', 'relation': '主張との関係', 'locator': '箇所',
    'additional_conditions': '追加条件', 'missing_information': '不足情報',
    'equipment_context': '装備', 'id': '識別ID', 'name': '名称', 'variant': '型式', 'region': '地域',
    'era': '時代', 'configuration': '構成', 'status': '状態', 'measurements': '数値',
    'equipment_id': '装備ID', 'quantity': '量', 'original_value': '値の原表記', 'unit': '単位',
    'value_kind': '値の種別', 'source_locator': '出典の箇所', 'calculation': '計算', 'inputs': '入力',
    'value': '値', 'assumption': '仮定', 'formula': '式', 'rounding': '丸め', 'decimal_places': '小数桁数',
    'military_context': '軍事分析の文脈', 'analysis_kind': '分析種別', 'analysis_levels': '分析階層',
    'subject': '対象', 'period': '時期', 'geography': '地理', 'actors': '当事者', 'objectives': '目的',
    'decision_point': '判断時点', 'available_information': '当時の情報', 'resources': '資源',
    'constraints': '制約', 'observed_outcome': '観測された結果', 'knowledge_basis': '情報の成立条件',
    'counterfactual_assumptions': '反実仮想の仮定', 'inference_context': '推論の申告',
    'claim_kind': '結論の種別', 'basis_kind': '根拠の種別', 'confounders': '交絡の検討項目',
    'identification': '因果を識別する方法', 'source_domain': '出典領域', 'source_type': '資料種別',
    'publisher_role': '発行主体との関係', 'modality': '形式', 'bibliography': '書誌',
    'author': '著者', 'title': '題名', 'year': '年', 'edition': '版', 'url': 'URL', 'doi': 'DOI',
    'access_status': '取得状態', 'method': '確認方法', 'read_range': '閲覧範囲', 'file_id': '保存ファイルID',
    'source_context': '資料の文脈', 'population': '対象集団', 'sample': '標本', 'comparison': '比較',
    'resistance': '抵抗条件', 'metrics': '測定指標', 'results': '結果', 'generalization': '一般化の範囲',
    'creation_date': '成立日', 'authorship': '成立主体', 'purpose': '作成目的',
    'access_constraints': '閲覧制約', 'retrospective': '回顧の条件', 'language': '言語',
    'translation': '翻訳', 'cited_sources': '引用元', 'setting_status': '設定の採用状態', 'content_role': '記載の役割'}


def render_report(record, result):
    """Render the same validated object; never turn an audit into a truth verdict."""
    if result['record_integrity'] != 'pass' or result['audit_status'] in ('error', 'blocked'):
        raise ValueError('不整合な記録は回答に変換しない')
    lines = ['# 調査回答', '', '> 判定は記録上の申告です。機械検査の通過は内容の正しさを保証しません。', '', '## 文脈', '']

    def fields(mapping, indent=''):
        for key, value in mapping.items():
            label = literal(LABELS.get(key, key))
            if isinstance(value, dict):
                lines.append(indent + '- ' + label + ':')
                fields(value, indent + '  ')
            elif isinstance(value, list) and value:
                lines.append(indent + '- ' + label + ':')
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        lines.append(indent + '  - 項目 ' + str(i + 1) + ':')
                        fields(item, indent + '    ')
                    else:
                        lines.append(indent + '  - ' + literal(item))
            else:
                lines.append(indent + '- ' + label + ': ' + ('記録なし' if value == [] else literal(value)))

    fields(record['context'])
    lines.extend(['', '## 主張と分析', ''])
    for finding in record['findings']:
        lines.extend(['### ' + literal(finding['id']), ''])
        fields({k: v for k, v in finding.items() if k not in ('id', 'assessments')})
        for assessment in finding['assessments']:
            lines.extend(['', '#### ' + literal(assessment['axis']) + ' — ' + literal(assessment['verdict']) + '（申告判定）', ''])
            fields({k: v for k, v in assessment.items() if k not in ('axis', 'verdict')})
        lines.append('')
    lines.extend(['## 出典', ''])
    for source in record['sources']:
        bibliography = source['bibliography']
        lines.extend(['### ' + literal(source['id']), ''])
        fields(source)
        url = safe_url(bibliography['url'])
        doi = doi_key(bibliography['doi'])
        if url:
            # Percent-encode Markdown delimiters, retaining the URL's semantics.
            lines.append('- [資料への直接リンク](' + quote(url, safe=':/?=&%+-._~') + ')')
        if doi:
            lines.append('- [DOI](https://doi.org/' + quote(doi, safe='/') + ')')
        lines.append('')
    lines.extend(['## 機械検査・要確認・未検証', '', '- 記録SHA-256: ' + result['record_sha256'],
                  '- 記録整合性: ' + result['record_integrity'], '- 監査状態: ' + result['audit_status'], ''])
    for check in result['audit_checks']:
        lines.append('- **' + literal(check['status']) + '** ' + literal(check['code']) + ' / ' + literal(check['at']) + ': ' + literal(check['message']))
        if check['details']:
            lines.append('  - ' + literal(json.dumps(check['details'], ensure_ascii=False, allow_nan=False)))
    return '\n'.join(lines) + '\n'
