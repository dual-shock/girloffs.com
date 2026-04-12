async function checkIfLive(username) {
  const url = `https://static-cdn.jtvnw.net/previews-ttv/live_user_${username}-1x1.jpg`;
  
  try {
    const response = await fetch(url, { method: 'HEAD', cache: 'no-store' });
    return response.ok && !response.url.includes('404_preview');
  } catch (error) {
    console.error("Error checking status:", error);
    return false;
  }
}

checkIfLive('mollyyxy').then(function(isLive) {
    streamIsLive = isLive;
    rebuildTwitchLink();
});

function rebuildTwitchLink() {
    var link = document.querySelector('.twitch-link');
    if (!link) return;
    var twitchWhite = document.querySelector('.twitch-icon-white-src');
    var hasOngoing = document.querySelector('.match.bracket-ongoing') !== null;

    var label;
    if (hasOngoing && streamIsLive) {
        label = 'Match Live now!';
    } else if (hasOngoing && !streamIsLive) {
        label = 'Starting up!';
    } else if (streamIsLive) {
        label = 'Live now!';
    } else {
        label = 'Offline';
    }

    link.textContent = '';
    link.classList.toggle('twitch-live', streamIsLive);
    link.classList.toggle('twitch-offline', !streamIsLive);
    link.href = 'https://twitch.tv/mollyyxy';
    link.appendChild(twitchWhite.cloneNode(true));
    link.appendChild(document.createTextNode(label));

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('new-tab-icon');
    svg.setAttribute('viewBox', '0 0 24 24');
    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M 3 3 L 3 21 L 21 21 L 21 12 L 19 12 L 19 19 L 5 19 L 5 5 L 12 5 L 12 3 L 3 3 z M 14 3 L 14 5 L 17.585938 5 L 8.2929688 14.292969 L 9.7070312 15.707031 L 19 6.4140625 L 19 10 L 21 10 L 21 3 L 14 3 z');
    svg.appendChild(path);
    link.appendChild(svg);
}

function activateTab(hash) {
    var validTabs = ['#bracket', '#schedule', '#players', '#results'];
    if (validTabs.indexOf(hash) === -1) return;
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    var navLink = document.querySelector('nav a[href="' + hash + '"]');
    if (navLink) navLink.classList.add('active');
    var section = document.querySelector(hash);
    if (section) section.classList.add('active');
    document.querySelector('main').classList.toggle('players-bg', hash === '#players');
    document.querySelector('main').classList.toggle('schedule-bg', hash === '#schedule');
}

document.querySelectorAll('nav a').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        activateTab(link.getAttribute('href'));
        if (link.getAttribute('href') === '#bracket') drawBracketLines();
    });
});

if (window.location.hash) {
    activateTab(window.location.hash);
}

const ROUND_KEYS = ['round_1', 'round_2', 'round_3', 'semis', 'final'];
const ROUND_LABELS = ['Round 1', 'Round 2', 'Quarterfinals', 'Semifinals', 'Final'];
const DAYS = {
    1: "11. April 2026",
    2: "12. April 2026",
    3: "18. April 2026",
    4: "19. April 2026",
}

const DAY_DATES = {
    1: "2026-04-11",
    2: "2026-04-12",
    3: "2026-04-18",
    4: "2026-04-19",
};

var bracketData = null;
var playerMap = {};
var countdownItems = [];
var streamIsLive = false;
var selectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone;

var TZ_LIST = [
    'Pacific/Auckland',
    'Australia/Sydney',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Asia/Kolkata',
    'Asia/Dubai',
    'Europe/Moscow',
    'Europe/Helsinki',
    'Europe/Berlin',
    'Europe/London',
    'America/Sao_Paulo',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Anchorage',
    'Pacific/Honolulu',
    'UTC'
];

function initTzSelector() {
    var select = document.getElementById('tz-select');
    var localTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    var tzSet = new Set(TZ_LIST);
    if (!tzSet.has(localTz)) TZ_LIST.unshift(localTz);
    TZ_LIST.forEach(function(tz) {
        var opt = document.createElement('option');
        opt.value = tz;
        var abbr = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'short' }).formatToParts(new Date()).find(function(p) { return p.type === 'timeZoneName'; });
        opt.textContent = abbr ? abbr.value : tz.replace(/_/g, ' ');
        if (tz === localTz) opt.selected = true;
        select.appendChild(opt);
    });
    select.addEventListener('change', function() {
        selectedTz = this.value;
        updateAllDisplayedTimes();
        resizeTzSelect(select);
    });
    resizeTzSelect(select);
}

function resizeTzSelect(select) {
    var tmp = document.createElement('span');
    tmp.style.visibility = 'hidden';
    tmp.style.position = 'absolute';
    tmp.style.whiteSpace = 'nowrap';
    tmp.style.font = getComputedStyle(select).font;
    tmp.textContent = select.options[select.selectedIndex].textContent;
    document.body.appendChild(tmp);
    select.style.width = tmp.offsetWidth + 'px';
    document.body.removeChild(tmp);
}

function formatTimeInTz(utcDate, tz) {
    return utcDate.toLocaleTimeString('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false });
}

function updateAllDisplayedTimes() {
    document.querySelectorAll('.schedule-time-box[data-utc]').forEach(function(el) {
        var d = new Date(el.dataset.utc);
        el.textContent = formatTimeInTz(d, selectedTz);
    });
}

initTzSelector();

function drawBracketLines() {
    var bracket = document.querySelector('.bracket');
    if (!bracket) return;

    var old = bracket.querySelector('.bracket-lines');
    if (old) old.remove();

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('bracket-lines');
    svg.setAttribute('width', bracket.scrollWidth);
    svg.setAttribute('height', bracket.scrollHeight);
    bracket.appendChild(svg);

    var rounds = Array.from(bracket.querySelectorAll('.round'));
    var roundMatches = rounds.map(function(r) {
        return Array.from(r.querySelectorAll('.match'));
    });

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

    var r1 = roundMatches[0] || [];
    var r2 = roundMatches[1] || [];
    for (var i = 0; i < r1.length && i < r2.length; i++) {
        var src = rel(r1[i]);
        var dstRows = r2[i].querySelectorAll('.match-row');
        var dstBottom = rel(dstRows[dstRows.length - 1]);
        var mx = (src.r + dstBottom.l) / 2;
        makeLine('M' + src.r + ' ' + src.cy + ' H' + mx + ' V' + dstBottom.cy + ' H' + dstBottom.l);
    }

    function pairConnect(si, di) {
        var sm = roundMatches[si] || [];
        var dm = roundMatches[di] || [];
        for (var i = 0; i < dm.length; i++) {
            if (i * 2 + 1 >= sm.length) break;
            var s1 = rel(sm[i * 2]);
            var s2 = rel(sm[i * 2 + 1]);
            var d = rel(dm[i]);
            var mx = (Math.max(s1.r, s2.r) + d.l) / 2;
            makeLine('M' + s1.r + ' ' + s1.cy + ' H' + mx + ' V' + d.cy + ' H' + d.l);
            makeLine('M' + s2.r + ' ' + s2.cy + ' H' + mx + ' V' + d.cy);
        }
    }

    pairConnect(1, 2);
    pairConnect(2, 3);
    pairConnect(3, 4);
}

function fetchBracket() {
    return fetch('data/bracket.json?t=' + Date.now())
        .then(function(r) { return r.json(); });
}

fetchBracket().then(function(data) {
    bracketData = data;
    data.players.forEach(function(p) {
        playerMap[p.name] = p;
    });

    var container = document.getElementById('bracket-container');

    ROUND_KEYS.forEach(function(key, i) {
        var round = document.createElement('div');
        round.className = 'round';

        var title = document.createElement('div');
        title.className = 'round-title';
        title.textContent = ROUND_LABELS[i];
        round.appendChild(title);

        var matchesWrap = document.createElement('div');
        matchesWrap.className = 'round-matches';

        var matches = data[key];
        if (!Array.isArray(matches)) matches = [matches];

        matches.forEach(function(match) {
            matchesWrap.appendChild(createMatch(match, playerMap));
        });

        round.appendChild(matchesWrap);
        container.appendChild(round);
    });

    if (data.bronze_final) {
        var bronzeWrap = document.createElement('div');
        bronzeWrap.className = 'bronze-final-wrap';

        var bronzeTitle = document.createElement('div');
        bronzeTitle.className = 'round-title';
        bronzeTitle.textContent = 'Bronze Final';
        bronzeWrap.appendChild(bronzeTitle);

        bronzeWrap.appendChild(createMatch(data.bronze_final, playerMap));
        container.appendChild(bronzeWrap);
    }

    buildSchedule(data, playerMap);
    buildPlayers(data);
    drawBracketLines();
    window.addEventListener('resize', drawBracketLines);

    setInterval(function() {
        fetchBracket().then(function(fresh) {
            bracketData = fresh;
            applyUpdate(fresh);
        });
    }, 60000);
});

function createMatch(match, playerMap) {
    const el = document.createElement('div');
    el.className = 'match';
    el.dataset.matchId = match.match_id;

    el.addEventListener('click', function(e) {
        if (e.target.closest('.player-name-link')) return;
        e.stopPropagation();
        showMatch(match.match_id);
    });

    el.appendChild(createRow(match.player_1, match.score.player_1, match.winner, playerMap));
    el.appendChild(createRow(match.player_2, match.score.player_2, match.winner, playerMap));

    return el;
}

function createRow(playerName, score, winner, playerMap) {
    const row = document.createElement('div');
    row.className = 'match-row';

    const player = playerMap[playerName];

    const seed = document.createElement('span');
    seed.className = 'player-seed';
    seed.textContent = player ? player.seed : '';

    const name = document.createElement('span');
    name.className = 'player-name';

    if (player) {
        var nameLink = document.createElement('a');
        nameLink.className = 'player-name-link';
        nameLink.href = '#';
        nameLink.dataset.player = playerName;
        nameLink.textContent = player.pref_name;
        nameLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showPlayer(playerName);
        });
        name.appendChild(nameLink);
    } else {
        var tbdSpan = document.createElement('span');
        tbdSpan.className = 'player-name-tbd';
        tbdSpan.textContent = playerName || 'TBD';
        name.appendChild(tbdSpan);
    }

    const scoreEl = document.createElement('span');
    scoreEl.className = 'player-score';
    scoreEl.textContent = score;

    if (winner && winner === playerName) {
        row.classList.add('winner');
    } else if (winner && winner !== playerName) {
        row.classList.add('loser');
    }

    row.appendChild(seed);
    row.appendChild(name);
    row.appendChild(scoreEl);
    return row;
}

function getMatchDate(match) {
    var dateStr = DAY_DATES[match.match_time.day];
    var time = match.match_time.utc_time || "00:00";
    return new Date(dateStr + "T" + time + ":00Z");
}

function buildSchedule(data, playerMap) {
    var allMatches = [];
    ROUND_KEYS.forEach(function(key) {
        var matches = data[key];
        if (!Array.isArray(matches)) matches = [matches];
        allMatches = allMatches.concat(matches);
    });
    if (data.bronze_final) allMatches.push(data.bronze_final);

    var byDay = {};
    allMatches.forEach(function(m) {
        var day = m.match_time.day;
        if (!byDay[day]) byDay[day] = [];
        byDay[day].push(m);
    });

    var sortedDays = Object.keys(byDay).sort(function(a, b) { return a - b; });
    var container = document.getElementById('schedule-container');

    sortedDays.forEach(function(day) {
        var matches = byDay[day].sort(function(a, b) {
            return getMatchDate(a) - getMatchDate(b);
        });

        var col = document.createElement('div');
        col.className = 'day-column';

        var title = document.createElement('div');
        title.className = 'day-title';
        title.textContent = DAYS[day];
        col.appendChild(title);

        var matchesWrap = document.createElement('div');
        matchesWrap.className = 'day-matches';

        matches.forEach(function(match) {
            var p1 = playerMap[match.player_1];
            var p2 = playerMap[match.player_2];
            var name1 = p1 ? p1.pref_name : match.player_1 || 'TBD';
            var name2 = p2 ? p2.pref_name : match.player_2 || 'TBD';

            var el = document.createElement('div');
            el.className = 'schedule-match';
            el.dataset.matchId = match.match_id;
            el.dataset.matchTime = getMatchDate(match).toISOString();

            var bothTbd = !playerMap[match.player_1] && !playerMap[match.player_2] && !match.match_time.utc_time;
            if (bothTbd) el.classList.add('schedule-match-tbd');

            var timeBox = document.createElement('div');
            timeBox.className = 'schedule-time-box pixel-box';
            var matchUtcDate = getMatchDate(match);
            if (match.match_time.utc_time) {
                timeBox.dataset.utc = matchUtcDate.toISOString();
                timeBox.textContent = formatTimeInTz(matchUtcDate, selectedTz);
            } else {
                timeBox.textContent = 'TBD';
            }

            var bar = document.createElement('div');
            bar.className = 'schedule-bar';

            var name1El = document.createElement('a');
            name1El.className = 'schedule-player';
            name1El.href = '#';
            if (match.winner === match.player_1) name1El.classList.add('schedule-winner');
            name1El.textContent = name1;
            if (match.player_1 && playerMap[match.player_1]) {
                name1El.dataset.player = match.player_1;
                name1El.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    showPlayer(this.dataset.player);
                });
            } else {
                name1El.classList.add('schedule-player-tbd');
            }

            var scoreEl = document.createElement('span');
            scoreEl.className = 'schedule-score';
            scoreEl.textContent = match.score.player_1 + ' - ' + match.score.player_2;

            var name2El = document.createElement('a');
            name2El.className = 'schedule-player';
            name2El.href = '#';
            if (match.winner === match.player_2) name2El.classList.add('schedule-winner');
            name2El.textContent = name2;
            if (match.player_2 && playerMap[match.player_2]) {
                name2El.dataset.player = match.player_2;
                name2El.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    showPlayer(this.dataset.player);
                });
            } else {
                name2El.classList.add('schedule-player-tbd');
            }

            var countdown = document.createElement('span');
            countdown.className = 'match-countdown';

            var vsEl = document.createElement('span');
            vsEl.className = 'schedule-vs';
            vsEl.textContent = 'vs';

            bar.appendChild(name1El);
            bar.appendChild(vsEl);
            bar.appendChild(name2El);
            bar.appendChild(scoreEl);
            bar.appendChild(countdown);

            el.appendChild(timeBox);
            el.appendChild(bar);
            matchesWrap.appendChild(el);

            el.addEventListener('click', function(e) {
                if (e.target.closest('.schedule-player')) return;
                document.querySelectorAll('.schedule-match').forEach(function(s) {
                    s.classList.remove('schedule-highlight');
                });
                el.classList.add('schedule-highlight');
            });

            countdownItems.push({ el: countdown, match: match, target: getMatchDate(match) });
        });

        col.appendChild(matchesWrap);
        container.appendChild(col);
    });

    updateCountdowns(countdownItems);
    updateBracketStatuses();
    setInterval(function() { updateCountdowns(countdownItems); updateBracketStatuses(); }, 1000);
    scrollToNearest(container);
}

function buildPlayers(data) {
    var rankedIconSrc = document.querySelector('.ranked-icon-src').src;
    var twitchIconSvg = document.querySelector('.twitch-icon-src');
    var container = document.getElementById('players-container');
    var sorted = data.players.slice().sort(function(a, b) { return a.seed - b.seed; });

    sorted.forEach(function(player) {
        var item = document.createElement('div');
        item.className = 'player-item';
        item.dataset.player = player.name;

        var avatar = document.createElement('img');
        avatar.className = 'player-avatar';
        avatar.src = 'https://mc-heads.net/avatar/' + player.name;
        avatar.alt = player.name;

        var info = document.createElement('div');
        info.className = 'player-info';

        var nameEl = document.createElement('div');
        nameEl.className = 'player-info-name';
        nameEl.textContent = player.name;

        var bottom = document.createElement('div');
        bottom.className = 'player-info-bottom';

        var prefName = document.createElement('span');
        prefName.className = 'player-pref-name';
        prefName.textContent = player.pref_name;

        var pronouns = document.createElement('span');
        pronouns.className = 'player-pronouns';
        pronouns.textContent = player.pronouns;

        bottom.appendChild(prefName);
        bottom.appendChild(pronouns);
        info.appendChild(nameEl);
        info.appendChild(bottom);

        var twitchLink = document.createElement('a');
        twitchLink.className = 'player-twitch-link';
        twitchLink.href = 'https://twitch.tv/' + player.twitch;
        twitchLink.target = '_blank';
        twitchLink.rel = 'noopener';
        twitchLink.appendChild(twitchIconSvg.cloneNode(true));

        var rankedLink = document.createElement('a');
        rankedLink.className = 'player-ranked-link';
        rankedLink.href = 'https://mcsrranked.com/stats/' + player.name;
        rankedLink.target = '_blank';
        rankedLink.rel = 'noopener';

        var rankedImg = document.createElement('img');
        rankedImg.src = rankedIconSrc;
        rankedImg.alt = 'Ranked';
        rankedLink.appendChild(rankedImg);

        var seedEl = document.createElement('span');
        seedEl.className = 'player-item-seed';
        seedEl.textContent = player.seed;

        var content = document.createElement('div');
        content.className = 'player-item-content';
        content.appendChild(avatar);
        content.appendChild(info);
        content.appendChild(twitchLink);
        content.appendChild(rankedLink);

        item.appendChild(seedEl);
        item.appendChild(content);
        container.appendChild(item);

        content.addEventListener('click', function(e) {
            if (e.target.closest('a')) return;
            document.querySelectorAll('.player-item').forEach(function(el) {
                el.classList.remove('player-highlight');
            });
            item.classList.add('player-highlight');
        });
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.player-item')) {
            document.querySelectorAll('.player-item').forEach(function(el) {
                el.classList.remove('player-highlight');
            });
        }
        if (!e.target.closest('.schedule-match') && !e.target.closest('.match')) {
            document.querySelectorAll('.schedule-match').forEach(function(el) {
                el.classList.remove('schedule-highlight');
            });
        }
    });
}

function updateCountdowns(items) {
    var now = new Date();
    var nextItem = null;
    var nextDiff = Infinity;

    items.forEach(function(item) {
        var diff = item.target - now;
        var matchEl = item.el.closest('.schedule-match');
        matchEl.classList.remove('match-upcoming', 'match-ongoing', 'match-finished', 'match-next');

        if (item.match.winner) {
            matchEl.classList.add('match-finished');
            item.el.textContent = '';
        } else if (diff <= 0) {
            matchEl.classList.add('match-ongoing');
            item.el.textContent = 'Live!';
        } else {
            matchEl.classList.add('match-upcoming');
            item.el.textContent = '';
            if (diff < nextDiff) {
                nextDiff = diff;
                nextItem = item;
            }
        }
    });

    if (nextItem) {
        var matchEl = nextItem.el.closest('.schedule-match');
        matchEl.classList.add('match-next');
        nextItem.el.textContent = 'Next!';

        var diff = nextItem.target - now;
        var h = Math.floor(diff / 3600000);
        var m = Math.floor((diff % 3600000) / 60000);
        var s = Math.floor((diff % 60000) / 1000);

        var headerEl = document.getElementById('header-countdown');
        var d = Math.floor(diff / 86400000);
        if (d >= 1) {
            headerEl.textContent = d + 'd ' + (h % 24) + 'h ' + m + 'm ' + s + 's';
        } else if (h >= 1) {
            headerEl.textContent = h + 'h ' + m + 'm ' + s + 's';
        } else {
            headerEl.textContent = m + 'm ' + s + 's';
        }
    } else {
        var headerEl = document.getElementById('header-countdown');
        headerEl.textContent = '--';
    }
}

function scrollToNearest(container) {
    if (window.innerWidth > 1024) return;
    var now = new Date();
    var best = null;
    var bestDiff = Infinity;
    container.querySelectorAll('.schedule-match').forEach(function(el) {
        var t = new Date(el.dataset.matchTime);
        var diff = t - now;
        if (diff >= 0 && diff < bestDiff) {
            bestDiff = diff;
            best = el;
        }
    });
    if (!best) {
        container.scrollTop = container.scrollHeight;
    } else {
        best.scrollIntoView({ block: 'nearest' });
    }
}

function applyUpdate(data) {
    var freshMap = {};
    data.players.forEach(function(p) { freshMap[p.name] = p; });

    var allRounds = ROUND_KEYS.slice();
    var allMatches = [];
    allRounds.forEach(function(key) {
        var m = data[key];
        if (!Array.isArray(m)) m = [m];
        allMatches = allMatches.concat(m);
    });
    if (data.bronze_final) allMatches.push(data.bronze_final);

    var matchById = {};
    allMatches.forEach(function(m) { matchById[m.match_id] = m; });

    document.querySelectorAll('.match[data-match-id]').forEach(function(el) {
        var match = matchById[el.dataset.matchId];
        if (!match) return;
        var rows = el.querySelectorAll('.match-row');
        updateBracketRow(rows[0], match.player_1, match.score.player_1, match.winner, freshMap);
        updateBracketRow(rows[1], match.player_2, match.score.player_2, match.winner, freshMap);
    });

    document.querySelectorAll('.schedule-match[data-match-id]').forEach(function(el) {
        var match = matchById[el.dataset.matchId];
        if (!match) return;
        var players = el.querySelectorAll('.schedule-player');
        var p1 = freshMap[match.player_1];
        var p2 = freshMap[match.player_2];
        players[0].textContent = p1 ? p1.pref_name : match.player_1 || 'TBD';
        players[1].textContent = p2 ? p2.pref_name : match.player_2 || 'TBD';
        players[0].classList.toggle('schedule-winner', match.winner === match.player_1 && !!match.winner);
        players[1].classList.toggle('schedule-winner', match.winner === match.player_2 && !!match.winner);
        var scoreEl = el.querySelector('.schedule-score');
        if (scoreEl) scoreEl.textContent = match.score.player_1 + ' - ' + match.score.player_2;
    });

    countdownItems.forEach(function(item) {
        var match = matchById[item.match.match_id];
        if (match) item.match = match;
    });
}

function updateBracketRow(row, playerName, score, winner, pMap) {
    var player = pMap[playerName];
    row.querySelector('.player-seed').textContent = player ? player.seed : '';
    var nameEl = row.querySelector('.player-name');
    var link = nameEl.querySelector('.player-name-link');
    if (player && link) {
        link.textContent = player.pref_name;
        link.dataset.player = playerName;
    } else if (player && !link) {
        nameEl.textContent = '';
        var newLink = document.createElement('a');
        newLink.className = 'player-name-link';
        newLink.href = '#';
        newLink.dataset.player = playerName;
        newLink.textContent = player.pref_name;
        newLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showPlayer(playerName);
        });
        nameEl.appendChild(newLink);
    } else {
        nameEl.textContent = '';
        var tbdSpan = document.createElement('span');
        tbdSpan.className = 'player-name-tbd';
        tbdSpan.textContent = playerName || 'TBD';
        nameEl.appendChild(tbdSpan);
    }
    row.querySelector('.player-score').textContent = score;
    row.classList.toggle('winner', !!winner && winner === playerName);
    row.classList.toggle('loser', !!winner && winner !== playerName);
}

function updateBracketStatuses() {
    var now = new Date();
    document.querySelectorAll('.match[data-match-id]').forEach(function(el) {
        var item = countdownItems.find(function(ci) {
            return String(ci.match.match_id) === el.dataset.matchId;
        });
        if (!item) return;
        el.classList.remove('bracket-ongoing', 'bracket-finished', 'bracket-upcoming');
        if (item.match.winner) {
            el.classList.add('bracket-finished');
        } else if (item.target - now <= 0) {
            el.classList.add('bracket-ongoing');
        } else {
            el.classList.add('bracket-upcoming');
        }
    });
    updateTwitchLinkText();
}

function updateTwitchLinkText() {
    rebuildTwitchLink();
}

function showPlayer(playerName) {
    document.querySelectorAll('nav a').forEach(function(a) { a.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(s) { s.classList.remove('active'); });
    document.querySelector('nav a[href="#players"]').classList.add('active');
    document.getElementById('players').classList.add('active');
    var m = document.querySelector('main');
    m.classList.add('players-bg');
    m.classList.remove('schedule-bg');

    document.querySelectorAll('.player-item').forEach(function(el) {
        el.classList.remove('player-highlight');
    });

    var target = document.querySelector('.player-item[data-player="' + playerName + '"]');
    if (target) {
        target.classList.add('player-highlight');
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
}

function showMatch(matchId) {
    document.querySelectorAll('nav a').forEach(function(a) { a.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(s) { s.classList.remove('active'); });
    document.querySelector('nav a[href="#schedule"]').classList.add('active');
    document.getElementById('schedule').classList.add('active');
    var m = document.querySelector('main');
    m.classList.add('schedule-bg');
    m.classList.remove('players-bg');

    document.querySelectorAll('.schedule-match').forEach(function(el) {
        el.classList.remove('schedule-highlight');
    });

    var target = document.querySelector('.schedule-match[data-match-id="' + matchId + '"]');
    if (target) {
        target.classList.add('schedule-highlight');
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
}
