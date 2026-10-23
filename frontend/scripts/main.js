import { activateTab } from './nav.js';
import { renderBracket, drawBracketLines, updateBracketStatuses } from './bracket.js';
import { initTzSelector, renderSchedule, updateCountdowns, scrollToNearest } from './schedule.js';
import { renderPlayers } from './players.js';
import { initCredits } from './credits.js';

// On girloffs.com and Cloudflare Pages previews the API lives on its own subdomain; locally the same server serves both.
const API_BASE = /(^|\.)girloffs\.com$|\.pages\.dev$/.test(location.hostname) ? 'https://api.girloffs.com' : '';
const REFRESH_MS = 10000;
const CACHE_KEY = 'girloffs-state';

var streamIsLive = false;
var countdownItems = [];
var lastRendered = null;

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

    var status = link.querySelector('.twitch-status');
    status.textContent = '';
    link.classList.toggle('twitch-live', streamIsLive);
    link.classList.toggle('twitch-offline', !streamIsLive);
    status.appendChild(twitchWhite.cloneNode(true));
    status.appendChild(document.createTextNode(label));
}

function render(state) {
    var playerMap = {};
    state.players.forEach(function(p) { playerMap[p.seed] = p; });

    // re-rendering replaces the content, so keep the user's scroll position
    var scrollers = ['.bracket-scroll', '#schedule-container', '#players-container'].map(s => document.querySelector(s));
    var saved = scrollers.map(el => [el.scrollTop, el.scrollLeft]);

    renderBracket(state, playerMap);
    countdownItems = renderSchedule(state, playerMap);
    renderPlayers(state);

    scrollers.forEach(function(el, i) { el.scrollTop = saved[i][0]; el.scrollLeft = saved[i][1]; });
    drawBracketLines();
    tick();
}

function tick() {
    updateCountdowns(countdownItems);
    updateBracketStatuses(countdownItems);
    rebuildTwitchLink();
}

function show(state) {
    var key = JSON.stringify([state.players, state.matches]);
    if (key === lastRendered) return;
    render(state);
    lastRendered = key;
}

// Fetches the latest state (Cloudflare serves it from a nearby cache) and re-renders if something changed.
// The last state is kept in localStorage so a returning visitor sees the bracket instantly, even if the API is down.
function refresh() {
    return fetch(API_BASE + '/api/state')
        .then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        })
        .then(function(state) {
            show(state);
            try { localStorage.setItem(CACHE_KEY, JSON.stringify(state)); } catch (e) {}
        });
}

function showCached() {
    try {
        var cached = localStorage.getItem(CACHE_KEY);
        if (cached) show(JSON.parse(cached));
    } catch (e) {}
}

function logError(err) {
    console.error('Could not load bracket state:', err);
}

document.querySelectorAll('nav a, .credits-link').forEach(link => {
    link.addEventListener('click', e => {
        if (!link.getAttribute('href')?.startsWith('#')) return;
        e.preventDefault();
        activateTab(link.getAttribute('href'));
        if (link.getAttribute('href') === '#bracket') drawBracketLines();
    });
});

if (window.location.hash) {
    activateTab(window.location.hash);
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('.schedule-match') && !e.target.closest('.match')) {
        document.querySelectorAll('.schedule-match').forEach(function(el) {
            el.classList.remove('schedule-highlight');
        });
    }
});

initTzSelector();
initCredits();

checkIfLive('mollyyxy').then(function(isLive) {
    streamIsLive = isLive;
    rebuildTwitchLink();
});

showCached();
refresh().catch(logError).then(function() {
    scrollToNearest(document.getElementById('schedule-container'));
    window.addEventListener('resize', drawBracketLines);
    setInterval(tick, 1000);
    setInterval(function() { refresh().catch(logError); }, REFRESH_MS);
});
