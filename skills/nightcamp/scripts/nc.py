#!/usr/bin/env python3
"""Query the Night Camp wiki dump (data/wiki.json, data/th.json).

  nc.py refresh                 re-download from play.nightcamp.app/wiki
  nc.py find <text>             search every name/id (English or Thai)
  nc.py show <id>               full record of any id (item, monster, map, job, set, material, quest, rune...)
  nc.py job <job_id>            job tree position + every skill (max-level numbers)
  nc.py drops <id|name>         which monsters drop it, rate, where they live
  nc.py map <map_id>            monsters on a map: level, element, race, armour
  nc.py items [filters]         list gear: slot=weapon wt=bow minlv=20 maxlv=40 r=epic el=fire set=1
  nc.py get <dotted.path>       raw subtree, e.g. s2.stats  s2.sw.W1  sys.refine  s2.runes.list.echo
  nc.py th <english text>       Thai text the wiki uses for that string
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
BASE = 'https://play.nightcamp.app/wiki/'


def load_js(text):
    return json.loads(text[text.index('{'):text.rindex('}') + 1])


def refresh():
    os.makedirs(DATA, exist_ok=True)
    html = urllib.request.urlopen(BASE + 'index.html').read().decode()
    import re
    v = re.search(r'data/wiki_en\.js\?v=([a-z0-9]+)', html)
    w = load_js(urllib.request.urlopen(BASE + 'data/wiki_en.js' + ('?v=' + v.group(1) if v else '')).read().decode())
    for k in ('atlas', 'hats128', 'sbBig'):  # sprite sheet coordinates, useless for questions
        w.pop(k, None)
    json.dump(w, open(os.path.join(DATA, 'wiki.json'), 'w'), ensure_ascii=False)
    th = load_js(urllib.request.urlopen(BASE + 'data/i18n_th.js').read().decode())
    json.dump(th.get('data', th), open(os.path.join(DATA, 'th.json'), 'w'), ensure_ascii=False)
    print('ok', w.get('season'), w.get('at'))


if sys.argv[1:2] == ['refresh']:
    refresh(); sys.exit()
if not os.path.exists(os.path.join(DATA, 'th.json')):  # data is not shipped with the skill; fetch on first use
    refresh()

W = json.load(open(os.path.join(DATA, 'wiki.json')))
TH = json.load(open(os.path.join(DATA, 'th.json')))
TH_REV = {v: k for k, v in TH.items()}
LISTS = ['jobs', 'monsters', 'maps', 'sets', 'bossSets', 'items', 'materials', 'quests', 'regions', 'life']
IDX = {}
for sec in LISTS:
    for r in W.get(sec, []):
        IDX.setdefault(r.get('id') or r.get('boss'), (sec, r))
for j in W['jobs']:
    for s in j['sk']:
        IDX.setdefault(s['id'], ('skill:' + j['id'], s))
for k, r in W['s2']['runes']['list'].items():
    IDX.setdefault('rune_' + k, ('rune', r))


def name(i):
    r = IDX.get(i)
    n = r[1].get('n', i) if r else W['skillNames'].get(i, i)
    return f"{n}" + (f" / {TH[n]}" if n in TH else '')


def pct(x):
    return f"{x * 100:.4g}%"


def cmd_find(q):
    q = TH_REV.get(q, q).lower()
    qs = {q} | {k.lower() for k, v in TH.items() if q in v.lower()}
    hits = [(sec, i, r.get('n', '')) for i, (sec, r) in IDX.items()
            if any(x in i.lower() or x in str(r.get('n', '')).lower() for x in qs)]
    for sec, i, n in hits[:80]:
        print(f"{sec:14} {i:32} {name(i)}")
    if len(hits) > 80: print(f"... {len(hits) - 80} more, narrow the search")
    if not hits: print('nothing; try a shorter word or English')


def cmd_show(i):
    if i not in IDX: return cmd_find(i)
    sec, r = IDX[i]
    print(sec, json.dumps(r, ensure_ascii=False, indent=1))
    for key in ('drops', 'mats'):
        if isinstance(r.get(key), list) and r[key] and isinstance(r[key][0], list):
            print(f"\n{key}:"); [print(f"  {pct(p):>8}  {name(x)}") for x, p in r[key]]
    if sec == 'monsters':
        print('\nmaps:', ', '.join(name(m) for m in r['maps']))


def cmd_job(i):
    j = IDX[i][1]
    chain, x = [], j
    while x: chain.insert(0, x['n']); x = IDX.get(x['from'], (0, None))[1] if x['from'] else None
    nexts = [k['n'] for k in W['jobs'] if k['from'] == j['id']]
    print(f"{name(j['id'])}  tier {j['tier']}  path: {' → '.join(chain)}" + (f"  → next: {', '.join(nexts)}" if nexts else ''))
    print(f"weapons: {', '.join(W['wtypes'].get(w, w) for w in j['wt'])} · HP/lv {j['hp']} SP/lv {j['sp']} · max job lv {j['maxJob']}")
    print(j['d'])
    lines = {l['id']: f"{l['n']}({l['el']})" for l in j['lines']}
    for s in j['sk']:
        last = s['lvs'][-1] if s.get('lvs') else [None] * 4
        nums = '' if last[0] is None else f" [max: {last[0]}% sp{last[1]} cd{last[2]}s" + (f" dur{last[3]}s" if last[3] else '') + ']'
        req = ', '.join(f"{name(a)} {b}" for a, b in (s['req'] or []))
        print(f"\n- {s['id']} · {name(s['id'])} · {lines.get(s['line'], s['line'])} · {s['kind'] or s['type']} · max {s['max']}{nums}"
              + (f" · needs {req}" if req else ''))
        print(f"  {s['d']}")


def cmd_drops(q):
    i = q if q in IDX else next((k for k, (s, r) in IDX.items() if str(r.get('n', '')).lower() == TH_REV.get(q, q).lower()), q)
    rows = [(p, m) for m in W['monsters'] for key in ('drops', 'mats') for x, p in m[key] if x == i]
    r = IDX.get(i, (0, {}))[1]
    print(name(i), '| src:', r.get('src') or r.get('from') or '-')
    for p, m in sorted(rows, key=lambda t: t[0], reverse=True):
        print(f"  {pct(p):>8}  {m['n']} (lv{m['lv']}{', BOSS' if m['boss'] else ''}) @ {', '.join(name(x) for x in m['maps'])}")
    for c in W['sys']['craft']:
        for x in c['list']:
            if x['id'] == i: print('  craft:', x['coins'], 'coins +', ', '.join(f"{name(a)}×{b}" for a, b in x['mats'].items()))
    if not rows: print('  no monster drops it (check src / craft / gacha)')


def cmd_map(i):
    m = IDX[i][1]
    print(name(i), m.get('lv'), m.get('kind'), '| zones:', ', '.join(m.get('zones', [])))
    fit = W['s2']['mapFit'].get(i)
    if fit: print('best style:', fit)
    for mid in m.get('mons', []):
        x = IDX.get(mid, (0, None))[1]
        if x: print(f"  {mid:22} {x['n']:28} lv{x['lv']:<3} el={x['el']:8} race={x['race']:9} armour={x['arm']:7} hp={x['hp']}{' BOSS' if x['boss'] else ''}")


def cmd_items(args):
    f = dict(a.split('=', 1) for a in args)
    out = []
    for it in W['items']:
        if 'slot' in f and it['s'] != f['slot']: continue
        if 'wt' in f and it.get('wt') != f['wt']: continue
        if 'r' in f and it['r'] != f['r']: continue
        if 'el' in f and it.get('el') != f['el']: continue
        if 'set' in f and not it.get('set'): continue
        if int(f.get('minlv', 0)) > it['lv'] or it['lv'] > int(f.get('maxlv', 999)): continue
        out.append(it)
    for it in sorted(out, key=lambda x: (x['lv'], x.get('atk', 0)))[:int(f.get('limit', 60))]:
        print(f"{it['id']:28} lv{it['lv']:<3} {it['r']:7} {it['s']:7} {it.get('wt', ''):8} atk={it.get('atk', '-')} el={it.get('el', '-')} st={it.get('st', '')} {it.get('ab', '')}")
    print(len(out), 'match')


def cmd_get(path):
    x = W
    for p in path.split('.'):
        x = x[int(p)] if isinstance(x, list) else x[p]
    print(json.dumps(x, ensure_ascii=False, indent=1))


cmds = {'find': cmd_find, 'show': cmd_show, 'job': cmd_job, 'drops': cmd_drops, 'map': cmd_map, 'get': cmd_get,
        'th': lambda q: print(TH.get(q, TH_REV.get(q, '(no translation)')))}
if len(sys.argv) < 3 and sys.argv[1:2] != ['items']:
    print(__doc__); sys.exit(1)
if sys.argv[1] == 'items':
    cmd_items(sys.argv[2:])
else:
    cmds[sys.argv[1]](' '.join(sys.argv[2:]))
