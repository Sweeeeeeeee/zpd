(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const captions = {
    given:
        'The tick marks show the equal sides AB and DE. Since these sides are also parallel, they form opposite sides of parallelogram ABDE.',
    triangles:
        'ABDE is a parallelogram, so AE = BD. The parallel sides give two matching angles in triangles AEF and DBC.',
    goal: 'The two triangles are congruent. Their corresponding sides give AF = CD and BC = EF.'
  };
  for (const button of el('hexagon').querySelectorAll('button')) {
    button.onclick = () => {
      el('hexagon').dataset.step = button.dataset.step;
      for (const item of el('hexagon').querySelectorAll('button'))
        item.setAttribute('aria-pressed', item === button);
      el('hex-caption').textContent = captions[button.dataset.step];
    };
  }

  const records = JSON.parse(el('record-data').textContent);
  const examples = [
    [
      'Quadrilateral midpoints',
      'a b c d = quadrangle a b c d;\ne = midpoint e a b;\nf = midpoint f b c;\ng = midpoint g c d;\nh = midpoint h d a\n? para e f g h'
    ],
    ['Triangle midline', 'a b c = triangle a b c;\nm = midpoint m a b;\nn = midpoint n a c\n? para m n b c'],
    ['Two halves of a segment', 'a b = segment a b;\nm = midpoint m a b\n? cong a m m b'],
    ['A claim that fails', 'a b c = triangle a b c;\nm = midpoint m a b\n? coll a m c']
  ];
  const startRecord = 'latvia/school/1999-00_50/grade10/p4';
  const initialShapes = {free: 1, segment: 2, triangle: 3, quadrangle: 4};
  const arities = {para: 4, cong: 4, coll: 3, midp: 3};
  const cap = name => name.toUpperCase();
  const segment = (a, b) => cap(a) + cap(b);
  function goalLabel(type, names) {
    const [a, b, c, d] = names;
    if (type === 'para' || type === 'cong')
      return segment(a, b) + (type === 'para' ? ' ∥ ' : ' = ') + segment(c, d);
    if (type === 'coll')
      return names.map(cap).join(', ') + ' collinear';
    return cap(a) + ' is the midpoint of ' + segment(b, c);
  }

  // Each free point is an independent vector. A common power-of-two denominator
  // makes all midpoint operations exact, even for nested constructions.
  function analyze(input) {
    if (input.length > 5000)
      throw Error('Use a construction under 5,000 characters.');
    const parts = input.trim().toLowerCase().split('?');
    if (parts.length !== 2 || !parts[0] || !parts[1].trim())
      throw Error('Separate the construction from one goal with a question mark (?).');
    const clauses = parts[0].split(';').map(s => s.trim()).filter(Boolean);
    if (clauses.length > 64)
      throw Error('Use at most 64 construction clauses.');
    const points = new Map(), free = [], edges = [], trace = [];
    const unit = 1n << BigInt(clauses.length);
    for (const clause of clauses) {
      const sides = clause.split('=').map(s => s.trim());
      if (sides.length !== 2 || !sides[0] || !sides[1])
        throw Error('Expected “point = construction” in: ' + clause);
      const names = sides[0].split(/\s+/), [op, ...args] = sides[1].split(/\s+/);
      for (const n of names) {
        if (!/^[a-z][a-z0-9_]{0,11}$/.test(n) || points.has(n) || names.filter(x => x === n).length > 1)
          throw Error(
              'Each point needs a unique name of up to 12 letters, digits or underscores, starting with a letter.');
      }
      if (Object.hasOwn(initialShapes, op)) {
        if (names.length !== initialShapes[op] || names.join(' ') !== args.join(' '))
          throw Error('List the same ' + initialShapes[op] + ' point names on both sides of ' + op + '.');
        for (const n of names) {
          points.set(n, new Map([[n, unit]]));
          free.push(n);
        }
        if (names.length > 1) {
          for (let i = 1; i < names.length; i++)
            edges.push([names[i - 1], names[i], 'given']);
          if (names.length > 2)
            edges.push([names.at(-1), names[0], 'given']);
        }
      } else if (op === 'midpoint') {
        const [n, a, b] = args;
        if (names.length !== 1 || args.length !== 3 || names[0] !== n || !points.has(a) || !points.has(b) ||
            a === b)
          throw Error('A midpoint needs two distinct, previously defined endpoints.');
        const v =
            new Map(free.map(k => [k, ((points.get(a).get(k) || 0n) + (points.get(b).get(k) || 0n)) / 2n]));
        points.set(n, v);
        edges.push([a, n, 'built'], [n, b, 'built']);
        trace.push(cap(n) + ' = (' + cap(a) + ' + ' + cap(b) + ') / 2');
      } else
        throw Error(
            '“' + op + '” is outside the browser checker. Open Recorded runs for the DD-AR experiments.');
    }
    const [type, ...args] = parts[1].trim().split(/\s+/);
    if (!Object.hasOwn(arities, type) || args.length !== arities[type])
      throw Error('Use one goal: para a b c d, cong a b c d, coll a b c, or midp m a b.');
    for (const n of args)
      if (!points.has(n))
        throw Error('The goal uses an undefined point: ' + n + '.');
    function diff(a, b) {
      return free.map(k => (points.get(b).get(k) || 0n) - (points.get(a).get(k) || 0n));
    }
    const [a, b, c, d] = args;
    const u = diff(a, b), v = d ? diff(c, d) : diff(a, c);
    if (!u.some(Boolean) || !v.some(Boolean))
      throw Error('The goal uses a segment with identical endpoints.');
    let proved, rule;
    if (type === 'para' || type === 'coll') {
      const pivot = u.findIndex(x => x !== 0n);
      proved = u.every((x, i) => x * v[pivot] === v[i] * u[pivot]);
      rule = 'The two direction vectors are proportional.';
    } else if (type === 'cong') {
      proved = u.every((x, i) => x === v[i]) || u.every((x, i) => x === -v[i]);
      rule = 'The segment vectors agree up to sign, so their lengths are equal.';
    } else {
      proved = u.every((x, i) => x === -v[i]);
      rule = 'The two endpoint vectors from the claimed midpoint are opposites.';
    }
    const describe = vec => vec.map((x, i) => x === 0n ? '' : String(x) + '·' + cap(free[i]))
                                .filter(Boolean)
                                .join(' + ')
                                .replaceAll('+ -', '− ') ||
        '0';
    trace.push(
        '', 'After substitution (common denominator ' + unit + '):',
        segment(a, b) + ' = (' + describe(u) + ') / ' + unit,
        (d ? segment(c, d) : segment(a, c)) + ' = (' + describe(v) + ') / ' + unit, '',
        proved ?
            rule :
            'The coefficient identity fails. The goal does not follow for all choices of the free points.');
    if (d)
      edges.push([a, b, 'goal'], [c, d, 'goal']);
    else
      edges.push([a, b, 'goal'], [a, c, 'goal']);
    const base = free.map((n, i) => {
      const theta = -Math.PI * .83 + i * 2 * Math.PI / free.length;
      return [Math.cos(theta) * (1 + .09 * (i % 2)), Math.sin(theta) * .72 + .05 * (i % 3)];
    });
    const coords = [...points.entries()].map(
        ([n, v]) =>
            [n,
             ...[0, 1].map(
                 j => free.reduce((z, k, i) => z + Number(v.get(k) || 0n) / Number(unit) * base[i][j], 0)),
             !free.includes(n)]);
    return {proved, goal: goalLabel(type, args), trace: trace.join('\n'), coords, edges, free: free.length};
  }

  const svg = el('drawing'), ns = 'http://www.w3.org/2000/svg';
  let lastFigure = null, mode = 'live';
  function draw(coords = [], edges = [], empty = 'No coordinates were saved for this run.') {
    lastFigure = [coords, edges, empty];
    svg.replaceChildren();
    el('empty-figure').hidden = !!coords.length;
    el('empty-figure').textContent = empty;
    el('point-count').textContent = coords.length ? coords.length + ' points' : '';
    svg.setAttribute(
        'aria-label',
        coords.length ? 'Construction with points ' + coords.map(p => cap(p[0])).join(', ') : empty);
    if (!coords.length)
      return;
    const loX = Math.min(...coords.map(p => p[1])), hiX = Math.max(...coords.map(p => p[1]));
    const loY = Math.min(...coords.map(p => p[2])), hiY = Math.max(...coords.map(p => p[2]));
    const scale = Math.min(490 / Math.max(.0001, hiX - loX), 245 / Math.max(.0001, hiY - loY));
    const available = new Map(coords.map(
        ([
          n, x, y, constructed
        ]) => [n, [310 + (x - (loX + hiX) / 2) * scale, 175 - (y - (loY + hiY) / 2) * scale, constructed]]));
    function node(tag, attr, label) {
      const n = document.createElementNS(ns, tag);
      for (const [k, v] of Object.entries(attr))
        n.setAttribute(k, v);
      if (label)
        n.textContent = label;
      svg.appendChild(n);
    }
    for (const [a, b, kind] of edges) {
      if (!available.has(a) || !available.has(b))
        continue;
      const [x, y] = available.get(a), [xx, yy] = available.get(b);
      node('line', {x1: x, y1: y, x2: xx, y2: yy, class: 'edge-' + kind});
    }
    for (const [n, [x, y, built]] of available) {
      node('circle', {cx: x, cy: y, r: 5, class: built ? 'dot-built' : 'dot-given'});
      if (el('labels').checked)
        node(
            'text', {
              x: x + (x < 310 ? -10 : 10),
              y: y + (y < 175 ? -10 : 19),
              'text-anchor': x < 310 ? 'end' : 'start'
            },
            cap(n));
    }
  }
  function readings(entries) {
    el('readings').replaceChildren();
    for (const [label, value] of entries) {
      const box = document.createElement('div'), k = document.createElement('span'),
            v = document.createElement('strong');
      k.className = 'small-label';
      k.textContent = label;
      v.textContent = value;
      box.append(k, v);
      el('readings').appendChild(box);
    }
  }
  function state(value, kind) {
    const s = el('scan-state');
    s.textContent = value;
    s.dataset.kind = kind;
    el('transcript').hidden = value === 'Ready' || kind === 'error';
  }
  function inspectRecord() {
    const row = records.find(x => x.id === el('example').value);
    const cfg = el('rules').value + (el('use-ar').checked ? '' : '_no_ar') + '-' + el('policy').value;
    const r = row.runs[cfg], proof = r.proof || '';
    const names = {
      proved: 'Proved',
      resource_limit: 'Resource limit',
      errors: 'Engine error',
      other_unproved: 'No proof found'
    };
    state(names[r.outcome], r.outcome === 'proved' ? 'pass' : 'neutral');
    el('goal-text').textContent = row.input.split('?').at(-1).trim();
    const aux = (r.aux || []).flatMap(a => a.clauses || []);
    el('result-text').textContent = aux.length ?
        'Recorded auxiliary construction: ' + aux.join('; ') :
        r.reason || 'The solver found a proof using the given construction.';
    el('trace-title').textContent = proof ? 'Recorded proof transcript' : 'Recorded input and outcome';
    el('trace').textContent = row.input + '\n\n' + (proof || r.reason || names[r.outcome]);
    readings([['Solver time', r.seconds + ' s'], ['Peak memory', r.memory + ' MiB']]);
    const coords = [...proof.matchAll(/^- ([^\s(]+)\((-?[\d.]+),\s*(-?[\d.]+)\)/gm)].map(
        m => [m[1], Number(m[2]), Number(m[3]), false]);
    const edges = [];
    const normalize = v => v.toUpperCase().replace(/[0-9]/g, c => '₀₁₂₃₄₅₆₇₈₉'[Number(c)]);
    for (const clause of row.input.split('?')[0].split(';')) {
      const [lhs, rhs] = clause.split('=').map(x => x.trim());
      if (!lhs || !rhs)
        continue;
      const pts = lhs.split(/\s+/).map(normalize);
      if (pts.length >= 3 && /triangle|quadrangle|parallelogram|square|trapezoid/.test(rhs)) {
        pts.forEach((n, i) => edges.push([n, pts[(i + 1) % pts.length], 'given']));
      }
    }
    for (const line of row.input.split('?').at(-1).split(';')) {
      const [op, a, b, c, d] = line.trim().split(/\s+/);
      if (['cong', 'para', 'perp'].includes(op) && d)
        edges.push([normalize(a), normalize(b), 'goal'], [normalize(c), normalize(d), 'goal']);
    }
    const proposed = new Set(aux.map(a => normalize(a.split('=')[0].trim())));
    coords.forEach(p => p[3] = proposed.has(p[0]));
    draw(coords, edges);
  }
  function scan() {
    el('input-status').textContent = '';
    try {
      if (mode === 'records') {
        inspectRecord();
        return;
      }
      const r = analyze(el('construction-input').value);
      state(r.proved ? 'Proved' : 'Not implied', r.proved ? 'pass' : 'neutral');
      el('goal-text').textContent = r.goal;
      el('result-text').textContent = r.proved ?
          'Exact vector arithmetic verifies the goal for every nondegenerate drawing.' :
          'The given construction allows drawings where this goal fails.';
      el('trace-title').textContent = 'Browser calculation';
      el('trace').textContent = r.trace;
      readings([['Free points', r.free], ['Midpoints', r.coords.length - r.free]]);
      draw(r.coords, r.edges);
    } catch (error) {
      state('Check input', 'error');
      el('goal-text').textContent = 'Input needs attention';
      el('result-text').textContent = error.message;
      readings([]);
      el('trace').textContent = '';
      el('input-status').textContent = error.message;
      draw([], [], 'Correct the input and run the scan again.');
    }
  }
  function pending() {
    state('Ready', 'neutral');
    el('input-status').textContent = '';
    el('goal-text').textContent = 'Awaiting scan';
    el('result-text').textContent = mode === 'live' ?
        'Run the scan to check the edited construction.' :
        'Load this configuration to inspect its recorded outcome.';
    readings([]);
    el('trace').textContent = '';
    el('transcript').open = false;
    draw([], [], 'The next scan will update this view.');
  }
  function chooseExample() {
    if (mode === 'live')
      el('construction-input').value = examples[Number(el('example').value)][1];
    scan();
  }
  function setMode(next) {
    mode = next;
    const live = mode === 'live';
    el('use-live').setAttribute('aria-pressed', live);
    el('use-records').setAttribute('aria-pressed', !live);
    el('live-fields').hidden = !live;
    el('record-fields').hidden = live;
    el('scan').querySelector('span').textContent = live ? 'Run scan' : 'Load record';
    el('example').replaceChildren();
    for (const [v, t] of (
             live ? examples.map(([n], i) => [String(i), n]) : records.map(r => [r.id, r.label]))) {
      el('example').add(new Option(t, v));
    }
    if (!live) {
      if (records.some(r => r.id === startRecord))
        el('example').value = startRecord;
      el('rules').value = 'circles';
      el('policy').value = 'combined';
      el('use-ar').checked = true;
    }
    el('transcript').open = false;
    chooseExample();
  }
  el('use-live').onclick = () => setMode('live');
  el('use-records').onclick = () => setMode('records');
  el('use-records').disabled = !records.length;
  el('example').onchange = chooseExample;
  el('reset').onclick = () => setMode(mode);
  el('scan').onclick = scan;
  el('construction-input').oninput = pending;
  el('construction-input').onkeydown = e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      scan();
    }
  };
  for (const key of ['policy', 'rules', 'use-ar'])
    el(key).onchange = pending;
  el('labels').onchange = () => {
    if (lastFigure)
      draw(...lastFigure);
  };
  setMode('live');
})();
