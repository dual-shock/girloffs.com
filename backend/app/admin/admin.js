// Girloffs admin panel. Talks only to /admin/api/*, which Cloudflare Access protects.
// Names come from the database and MCSR, so everything is inserted as text, never as HTML.

var ROUNDS = ['Round 1', 'Round 2', 'Quarterfinal', 'Semifinal', 'Final'];
var REFRESH_MS = 10000;

var data = null;
var dirty = {};  // form key -> true while it has unsaved changes; auto-refresh waits until they're saved

function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function(k) {
        if (k === 'class') node.className = props[k];
        else if (k === 'text') node.textContent = props[k];
        else if (k.slice(0, 2) === 'on') node.addEventListener(k.slice(2), props[k]);
        else node[k] = props[k];
    });
    (children || []).forEach(function(c) { if (c !== null && c !== undefined) node.append(c); });
    return node;
}

function api(method, path, body) {
    var opts = { method: method, headers: {}, cache: 'no-store' };
    if (body !== undefined) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    }
    return fetch('/admin/api/' + path, opts).then(function(r) {
        return r.json().catch(function() { return {}; }).then(function(json) {
            if (!r.ok) {
                var detail = typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail || '');
                throw new Error(detail || 'HTTP ' + r.status);
            }
            return json;
        });
    }, function() {
        throw new Error("Can't reach the server, or your login expired. Reload the page.");
    });
}

function showError(message) {
    var box = document.getElementById('error');
    box.textContent = message + '  (click to hide)';
    box.hidden = false;
}

function hideError() {
    document.getElementById('error').hidden = true;
}

function playerName(seed) {
    var p = data.state.players.find(function(p) { return p.seed === seed; });
    return p ? p.display_name + ' (' + seed + ')' : 'seed ' + seed;
}

function sourceLabel(source) {
    var parts = source.split(':');
    if (parts[0] === 'seed') return 'seed ' + parts[1];
    return (parts[0] === 'winner' ? 'Winner of #' : 'Loser of #') + parts[1];
}

function fmtTime(iso) {
    return iso ? iso.slice(0, 16).replace('T', ' ') : '';
}

function fmtEpoch(seconds) {
    return new Date(seconds * 1000).toISOString().slice(11, 16);
}

function fmtDuration(ms) {
    if (ms === null || ms === undefined) return '–';
    var s = Math.round(ms / 1000);
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}

function trackDirty(container, key, save) {
    function mark() {
        dirty[key] = true;
        container.classList.add('dirty');
        save.disabled = false;
        renderStatus();
    }
    container.addEventListener('input', mark);
    container.addEventListener('change', mark);
}

function submit(key, save, request, label) {
    save.disabled = true;
    request.then(function() {
        delete dirty[key];
        hideError();
        return load();
    }).catch(function(e) {
        save.disabled = false;
        showError(label + ': ' + e.message);
    });
}

function setExcluded(id, excluded) {
    api('POST', 'games/' + id, { excluded: excluded }).then(function() {
        hideError();
        return load();
    }).catch(function(e) { showError('Game ' + id + ': ' + e.message); });
}

function matchCard(m, seedByUuid) {
    var raw = data.matches.find(function(r) { return r.number === m.number; });
    var key = 'm' + m.number;
    var card = el('div', { class: 'match', id: 'match-' + m.number });

    var names = m.players.map(function(s, i) { return s !== null ? playerName(s) : sourceLabel(m.sources[i]); });
    card.append(
        el('div', { class: 'match-head' }, [
            el('b', { text: '#' + m.number }),
            el('span', { text: m.third_place ? '3rd place match' : ROUNDS[m.round - 1] }),
            el('span', { class: 'badge ' + m.status, text: m.status + (m.forfeit ? ' (forfeit)' : '') }),
            m.winner !== null ? el('span', { text: 'winner: ' + playerName(m.winner) }) : null,
        ]),
        el('div', { class: 'versus' }, [names[0], el('span', { class: 'score', text: m.score[0] + ' – ' + m.score[1] }), names[1]])
    );

    var time = el('input', { value: fmtTime(raw.scheduled_at), placeholder: 'YYYY-MM-DD HH:MM', size: 16 });
    var bestOf = el('select', {}, [1, 3, 5, 7].map(function(n) {
        return el('option', { value: n, text: 'Bo' + n, selected: n === raw.best_of });
    }));
    var winner = el('select', {}, [el('option', { value: '', text: 'Automatic (from games)' })]);
    m.players.forEach(function(s) {
        if (s !== null) winner.append(el('option', { value: s, text: playerName(s), selected: raw.winner_override === s }));
    });
    if (raw.winner_override !== null && m.players.indexOf(raw.winner_override) === -1) {
        winner.append(el('option', { value: raw.winner_override, selected: true,
            text: playerName(raw.winner_override) + ' (not in this match, ignored)' }));
    }
    var forfeit = el('input', { type: 'checkbox', checked: !!raw.forfeit });
    var score = el('input', { value: raw.score_override || '', placeholder: 'automatic', size: 8 });
    var save = el('button', { type: 'button', class: 'primary', text: 'Save', disabled: true });

    var fields = el('div', { class: 'fields' }, [
        el('label', {}, ['Start (UTC)', time]),
        el('label', {}, ['Best of', bestOf]),
        el('label', {}, ['Winner', winner]),
        el('label', { class: 'check' }, [forfeit, 'forfeit / no-show']),
        el('label', {}, ['Score override (slot 1 first)', score]),
        save,
    ]);
    trackDirty(fields, key, save);
    save.addEventListener('click', function() {
        submit(key, save, api('POST', 'matches/' + m.number, {
            scheduled_at: time.value.trim() || null,
            best_of: Number(bestOf.value),
            winner_override: winner.value === '' ? null : Number(winner.value),
            forfeit: forfeit.checked,
            score_override: score.value.trim() || null,
        }), 'Match ' + m.number);
    });
    card.append(fields);

    var counted = m.games.map(function(g) { return g.id; });
    var games = data.games.filter(function(g) { return g.match_number === m.number; });
    if (!games.length) {
        card.append(el('p', { class: 'muted', text: 'No games recorded yet.' }));
        return card;
    }
    card.append(el('ul', { class: 'games' }, games.map(function(g) {
        var state = g.excluded ? 'excluded' : counted.indexOf(g.mcsr_id) !== -1 ? 'counted' : 'ignored';
        var label = { excluded: 'excluded', counted: 'counts', ignored: "doesn't count: not these two players" }[state];
        var winnerSeed = seedByUuid[g.winner_uuid];
        return el('li', {}, [
            el('span', { class: state, text: 'Game ' + g.mcsr_id }),
            el('span', { text: fmtEpoch(g.played_at) + ' UTC' }),
            el('span', { text: g.winner_uuid ? 'won by ' + (winnerSeed ? playerName(winnerSeed) : 'unknown account') : 'draw' }),
            el('span', { text: fmtDuration(g.duration_ms) + (g.forfeited ? ' (forfeit)' : '') }),
            el('span', { class: 'muted', text: label }),
            el('button', { type: 'button', text: g.excluded ? 'Count it again' : 'Exclude',
                onclick: function() { setExcluded(g.mcsr_id, !g.excluded); } }),
        ]);
    })));
    return card;
}

function renderMatches() {
    var seedByUuid = {};
    data.state.players.forEach(function(p) { seedByUuid[p.uuid] = p.seed; });
    var hideFinished = document.getElementById('hide-finished').checked;
    var matches = data.state.matches.slice().sort(function(a, b) { return a.number - b.number; });
    var section = document.getElementById('matches');
    section.replaceChildren(el('h2', { text: 'Matches' }));
    matches.forEach(function(m) {
        if (!(hideFinished && m.status === 'finished')) section.append(matchCard(m, seedByUuid));
    });
}

function renderPlayers() {
    var rows = data.state.players.map(function(p) {
        var key = 'p' + p.seed;
        var inputs = {
            mc_name: el('input', { value: p.mc_name }),
            display_name: el('input', { value: p.display_name }),
            pronouns: el('input', { value: p.pronouns }),
            twitch: el('input', { value: p.twitch }),
        };
        var save = el('button', { type: 'button', class: 'primary', text: 'Save', disabled: true });
        var row = el('tr', {}, [
            el('td', { text: p.seed }),
            el('td', {}, [inputs.mc_name]),
            el('td', {}, [inputs.display_name]),
            el('td', {}, [inputs.pronouns]),
            el('td', {}, [inputs.twitch]),
            el('td', {}, [el('code', { text: p.uuid || '' })]),
            el('td', {}, [save]),
        ]);
        trackDirty(row, key, save);
        save.addEventListener('click', function() {
            var name = inputs.mc_name.value.trim();
            if (name !== p.mc_name && !confirm('Replace seed ' + p.seed + "'s Minecraft account with " + name +
                    '? Games played under the old account stop counting.')) return;
            submit(key, save, api('POST', 'players/' + p.seed, {
                mc_name: name,
                display_name: inputs.display_name.value.trim(),
                pronouns: inputs.pronouns.value.trim(),
                twitch: inputs.twitch.value.trim(),
            }), 'Player ' + p.seed);
        });
        return row;
    });
    var head = el('tr', {}, ['Seed', 'Minecraft name', 'Display name', 'Pronouns', 'Twitch', 'UUID', ''].map(function(t) {
        return el('th', { text: t });
    }));
    document.getElementById('players').replaceChildren(el('table', {}, [el('thead', {}, [head]), el('tbody', {}, rows)]));
}

function describe(details) {
    var d = JSON.parse(details);
    return Object.keys(d).map(function(field) {
        var show = function(v) { return v === null ? 'none' : String(v); };
        return field + ': ' + show(d[field][0]) + ' → ' + show(d[field][1]);
    }).join(', ');
}

function renderAudit() {
    var rows = data.audit.map(function(a) {
        return el('tr', {}, [
            el('td', { text: fmtTime(a.at) + ' UTC' }),
            el('td', { text: a.email }),
            el('td', { text: a.action }),
            el('td', { text: describe(a.details) }),
        ]);
    });
    if (!rows.length) rows = [el('tr', {}, [el('td', { class: 'muted', text: 'No changes yet.', colSpan: 4 })])];
    var head = el('tr', {}, ['When', 'Who', 'What', 'Change'].map(function(t) { return el('th', { text: t }); }));
    document.getElementById('audit').replaceChildren(el('table', {}, [el('thead', {}, [head]), el('tbody', {}, rows)]));
}

function renderStatus() {
    if (!data) return;
    var p = data.poller;
    var poll = p.last_error ? 'MCSR poller error: ' + p.last_error
        : p.last_ok ? 'MCSR last checked ' + p.last_ok.slice(11, 19) + ' UTC' : 'MCSR not checked yet';
    var refresh = Object.keys(dirty).length ? 'auto-refresh paused: unsaved changes' : 'auto-refresh every 10 s';
    document.getElementById('status').textContent = 'Signed in as ' + data.email + ' · ' + poll + ' · ' + refresh;
}

function render() {
    renderMatches();
    renderPlayers();
    renderAudit();
    renderStatus();
}

function isEditing() {
    var a = document.activeElement;
    return a && (a.tagName === 'INPUT' || a.tagName === 'SELECT') && a.closest('main');
}

// Never re-render over unsaved changes or while someone is typing.
function load() {
    if (Object.keys(dirty).length || isEditing()) {
        renderStatus();
        return Promise.resolve();
    }
    return api('GET', 'state').then(function(d) {
        data = d;
        render();
    }).catch(function(e) { showError(e.message); });
}

document.getElementById('refresh').addEventListener('click', function() {
    if (Object.keys(dirty).length) showError('Save your changes first, or reload the page to throw them away.');
    load();
});
document.getElementById('error').addEventListener('click', hideError);
document.getElementById('hide-finished').addEventListener('change', function() {
    if (data && !Object.keys(dirty).length) render();
});

load();
setInterval(load, REFRESH_MS);
