import { showPlayer, showMatch } from './nav.js';

const ROUND_LABELS = ['Round 1', 'Round 2', 'Quarterfinals', 'Semifinals', 'Final'];

export function renderBracket(state, playerMap) {
    var container = document.getElementById('bracket-container');
    container.textContent = '';

    var bracketMatches = state.matches.filter(m => !m.third_place);
    var byNumber = {};
    state.matches.forEach(m => { byNumber[m.number] = m; });
    var rounds = Array.from(new Set(bracketMatches.map(m => m.round))).sort((a, b) => a - b);

    rounds.forEach(function(r, i) {
        var round = document.createElement('div');
        round.className = 'round';

        var title = document.createElement('div');
        title.className = 'round-title';
        title.textContent = ROUND_LABELS[i];
        round.appendChild(title);

        var matchesWrap = document.createElement('div');
        matchesWrap.className = 'round-matches';

        roundColumn(bracketMatches, r).forEach(function(match) {
            matchesWrap.appendChild(match ? createMatch(match, playerMap, byNumber) : createSpacer());
        });

        round.appendChild(matchesWrap);
        container.appendChild(round);
    });

    var bronze = state.matches.find(m => m.third_place);
    if (bronze) {
        var bronzeWrap = document.createElement('div');
        bronzeWrap.className = 'bronze-final-wrap';

        var bronzeTitle = document.createElement('div');
        bronzeTitle.className = 'round-title';
        bronzeTitle.textContent = 'Bronze Final';
        bronzeWrap.appendChild(bronzeTitle);

        bronzeWrap.appendChild(createMatch(bronze, playerMap, byNumber));
        container.appendChild(bronzeWrap);
    }
}

// Round 1 has fewer matches than round 2 (top seeds have byes), so each round 1 match is placed
// next to the round 2 match it feeds, with an empty spacer next to round 2 matches that have no feeder.
function roundColumn(matches, round) {
    var inRound = matches.filter(m => m.round === round).sort((a, b) => a.position - b.position);
    var nextRound = matches.filter(m => m.round === round + 1).sort((a, b) => a.position - b.position);
    if (nextRound.length < inRound.length) return inRound;
    return nextRound.map(target => inRound.find(m => m.next === target.number) || null);
}

function createSpacer() {
    var el = document.createElement('div');
    el.className = 'match';
    el.style.visibility = 'hidden';
    el.appendChild(createRow(null, '', null, {}));
    el.appendChild(createRow(null, '', null, {}));
    return el;
}

function createMatch(match, playerMap, byNumber) {
    const el = document.createElement('div');
    el.className = 'match';
    el.dataset.matchId = match.number;
    if (match.next) {
        el.dataset.next = match.next;
        el.dataset.nextSlot = byNumber[match.next].sources.indexOf('winner:' + match.number);
    }

    el.addEventListener('click', function(e) {
        if (e.target.closest('.player-name-link')) return;
        e.stopPropagation();
        showMatch(match.number);
    });

    el.appendChild(createRow(match.players[0], match.score[0], match.winner, playerMap));
    el.appendChild(createRow(match.players[1], match.score[1], match.winner, playerMap));

    return el;
}

function createRow(seed, score, winner, playerMap) {
    const row = document.createElement('div');
    row.className = 'match-row';

    const player = playerMap[seed];

    const seedEl = document.createElement('span');
    seedEl.className = 'player-seed';
    seedEl.textContent = player ? player.seed : '';

    const name = document.createElement('span');
    name.className = 'player-name';

    if (player) {
        var nameLink = document.createElement('a');
        nameLink.className = 'player-name-link';
        nameLink.href = '#';
        nameLink.dataset.seed = seed;
        nameLink.textContent = player.display_name;
        nameLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showPlayer(seed);
        });
        name.appendChild(nameLink);
    } else {
        var tbdSpan = document.createElement('span');
        tbdSpan.className = 'player-name-tbd';
        tbdSpan.textContent = 'TBD';
        name.appendChild(tbdSpan);
    }

    const scoreEl = document.createElement('span');
    scoreEl.className = 'player-score';
    scoreEl.textContent = score;

    if (winner && winner === seed) {
        row.classList.add('winner');
    } else if (winner) {
        row.classList.add('loser');
    }

    row.appendChild(seedEl);
    row.appendChild(name);
    row.appendChild(scoreEl);
    return row;
}

export function drawBracketLines() {
    var bracket = document.querySelector('.bracket');
    if (!bracket) return;

    var old = bracket.querySelector('.bracket-lines');
    if (old) old.remove();

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('bracket-lines');
    svg.setAttribute('width', bracket.scrollWidth);
    svg.setAttribute('height', bracket.scrollHeight);
    bracket.appendChild(svg);

    var bRect = bracket.getBoundingClientRect();

    function rel(el) {
        var r = el.getBoundingClientRect();
        return {
            l: r.left - bRect.left,
            r: r.right - bRect.left,
            t: r.top - bRect.top,
            b: r.bottom - bRect.top,
            cy: (r.top + r.bottom) / 2 - bRect.top
        };
    }

    function makeLine(d) {
        var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        p.setAttribute('d', d);
        var lineColor = getComputedStyle(document.documentElement).getPropertyValue('--bracket-line-color').trim() || 'rgba(255,255,255,0.15)';
        p.setAttribute('stroke', lineColor);
        p.setAttribute('stroke-width', '1.5');
        p.setAttribute('fill', 'none');
        svg.appendChild(p);
    }

    var feeders = {};
    bracket.querySelectorAll('.round .match[data-next]').forEach(function(el) {
        (feeders[el.dataset.next] = feeders[el.dataset.next] || []).push(el);
    });

    Object.keys(feeders).forEach(function(next) {
        var dst = bracket.querySelector('.round .match[data-match-id="' + next + '"]');
        if (!dst) return;
        var srcs = feeders[next];

        if (srcs.length === 1) {
            // only one match feeds this one (the other slot is a seeded player): connect to the row it fills
            var src = rel(srcs[0]);
            var row = rel(dst.querySelectorAll('.match-row')[srcs[0].dataset.nextSlot]);
            var mx = (src.r + row.l) / 2;
            makeLine('M' + src.r + ' ' + src.cy + ' H' + mx + ' V' + row.cy + ' H' + row.l);
            return;
        }

        var d = rel(dst);
        var rects = srcs.map(rel);
        var mx2 = (Math.max.apply(null, rects.map(s => s.r)) + d.l) / 2;
        rects.forEach(function(s, i) {
            makeLine('M' + s.r + ' ' + s.cy + ' H' + mx2 + ' V' + d.cy + (i === 0 ? ' H' + d.l : ''));
        });
    });
}

export function updateBracketStatuses(countdownItems) {
    var now = new Date();
    document.querySelectorAll('.match[data-match-id]').forEach(function(el) {
        var item = countdownItems.find(function(ci) {
            return String(ci.match.number) === el.dataset.matchId;
        });
        if (!item) return;
        el.classList.remove('bracket-ongoing', 'bracket-finished', 'bracket-upcoming');
        if (item.match.winner) {
            el.classList.add('bracket-finished');
        } else if (item.target && item.target - now <= 0) {
            el.classList.add('bracket-ongoing');
        } else {
            el.classList.add('bracket-upcoming');
        }
    });
}
