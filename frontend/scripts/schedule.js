import { showPlayer } from './nav.js';

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

export function initTzSelector() {
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

// "2026-10-24" -> "24. October 2026"
function formatDay(day) {
    var d = new Date(day + 'T00:00:00Z');
    return d.getUTCDate() + '. ' + d.toLocaleString('en-GB', { month: 'long', timeZone: 'UTC' }) + ' ' + d.getUTCFullYear();
}

function matchDate(match) {
    return match.scheduled_at ? new Date(match.scheduled_at) : null;
}

// Builds the schedule tab and returns the countdown items the 1-second ticker updates.
export function renderSchedule(state, playerMap) {
    var container = document.getElementById('schedule-container');
    container.textContent = '';
    var countdownItems = [];

    var byDay = {};
    state.matches.forEach(function(m) {
        var day = m.day || 'TBD';
        if (!byDay[day]) byDay[day] = [];
        byDay[day].push(m);
    });

    Object.keys(byDay).sort().forEach(function(day) {
        var matches = byDay[day].sort(function(a, b) {
            return (matchDate(a) || Infinity) - (matchDate(b) || Infinity);
        });

        var col = document.createElement('div');
        col.className = 'day-column';

        var title = document.createElement('div');
        title.className = 'day-title';
        title.textContent = day === 'TBD' ? 'TBD' : formatDay(day);
        col.appendChild(title);

        var matchesWrap = document.createElement('div');
        matchesWrap.className = 'day-matches';

        matches.forEach(function(match) {
            var p1 = playerMap[match.players[0]];
            var p2 = playerMap[match.players[1]];

            var el = document.createElement('div');
            el.className = 'schedule-match';
            el.dataset.matchId = match.number;
            if (match.scheduled_at) el.dataset.matchTime = match.scheduled_at;

            if (!p1 && !p2 && !match.scheduled_at) el.classList.add('schedule-match-tbd');

            var timeBox = document.createElement('div');
            timeBox.className = 'schedule-time-box pixel-box';
            var start = matchDate(match);
            if (start) {
                timeBox.dataset.utc = start.toISOString();
                timeBox.textContent = formatTimeInTz(start, selectedTz);
            } else {
                timeBox.textContent = 'TBD';
            }

            var bar = document.createElement('div');
            bar.className = 'schedule-bar';

            var scoreEl = document.createElement('span');
            scoreEl.className = 'schedule-score';
            scoreEl.textContent = match.score[0] + ' - ' + match.score[1];

            var countdown = document.createElement('span');
            countdown.className = 'match-countdown';

            var vsEl = document.createElement('span');
            vsEl.className = 'schedule-vs';
            vsEl.textContent = 'vs';

            bar.appendChild(createName(match.players[0], p1, match.winner));
            bar.appendChild(vsEl);
            bar.appendChild(createName(match.players[1], p2, match.winner));
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

            countdownItems.push({ el: countdown, match: match, target: start });
        });

        col.appendChild(matchesWrap);
        container.appendChild(col);
    });

    return countdownItems;
}

function createName(seed, player, winner) {
    var nameEl = document.createElement('a');
    nameEl.className = 'schedule-player';
    nameEl.href = '#';
    if (winner && winner === seed) nameEl.classList.add('schedule-winner');
    nameEl.textContent = player ? player.display_name : 'TBD';
    if (player) {
        nameEl.dataset.seed = seed;
        nameEl.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showPlayer(seed);
        });
    } else {
        nameEl.classList.add('schedule-player-tbd');
    }
    return nameEl;
}

export function updateCountdowns(items) {
    var now = new Date();
    var nextItem = null;
    var nextDiff = Infinity;

    items.forEach(function(item) {
        var diff = item.target ? item.target - now : Infinity;
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

    var headerEl = document.getElementById('header-countdown');
    if (nextItem) {
        var matchEl = nextItem.el.closest('.schedule-match');
        matchEl.classList.add('match-next');
        nextItem.el.textContent = 'Next!';

        var diff = nextDiff;
        var h = Math.floor(diff / 3600000);
        var m = Math.floor((diff % 3600000) / 60000);
        var s = Math.floor((diff % 60000) / 1000);
        var d = Math.floor(diff / 86400000);
        if (d >= 1) {
            headerEl.textContent = d + 'd ' + (h % 24) + 'h ' + m + 'm ' + s + 's';
        } else if (h >= 1) {
            headerEl.textContent = h + 'h ' + m + 'm ' + s + 's';
        } else {
            headerEl.textContent = m + 'm ' + s + 's';
        }
    } else {
        headerEl.textContent = '--';
    }
}

export function scrollToNearest(container) {
    if (window.innerWidth > 1024) return;
    var now = new Date();
    var best = null;
    var bestDiff = Infinity;
    container.querySelectorAll('.schedule-match').forEach(function(el) {
        if (!el.dataset.matchTime) return;
        var diff = new Date(el.dataset.matchTime) - now;
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
