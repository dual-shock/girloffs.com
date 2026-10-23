import { featurePlayer } from './players.js';

export function activateTab(hash) {
    var validTabs = ['#bracket', '#schedule', '#players', '#results', '#credits'];
    if (validTabs.indexOf(hash) === -1) return;
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    var navLink = document.querySelector('nav a[href="' + hash + '"]');
    if (navLink) navLink.classList.add('active');
    var section = document.querySelector(hash);
    if (section) section.classList.add('active');
    setLineupBg(hash === '#players');
}

// show the lineup only once it's actually playing, so a slow download never shows an empty frame
function setLineupBg(on) {
    var video = document.querySelector('.bg-lineup');
    if (on && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        video.play().then(() => document.body.classList.add('lineup-bg'), () => {});
    } else {
        document.body.classList.remove('lineup-bg');
        video.pause();
    }
}

// iOS Low Power Mode blocks autoplay, so the background can still be paused: any tap starts it
function resumeBackground() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('lineup-bg')) return;
    if (document.querySelector('#players.active')) {
        setLineupBg(true);
    } else {
        var gradient = document.querySelector('.bg-gradient');
        if (gradient.paused) gradient.play().catch(() => {});
    }
}
document.addEventListener('touchend', resumeBackground);
document.addEventListener('click', resumeBackground);

export function showPlayer(seed) {
    activateTab('#players');
    featurePlayer(seed);
}

export function showMatch(number) {
    activateTab('#schedule');
    document.querySelectorAll('.schedule-match').forEach(function(el) {
        el.classList.remove('schedule-highlight');
    });
    var target = document.querySelector('.schedule-match[data-match-id="' + number + '"]');
    if (target) {
        target.classList.add('schedule-highlight');
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
}
