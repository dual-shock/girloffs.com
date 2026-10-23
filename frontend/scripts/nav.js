export function activateTab(hash) {
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

export function showPlayer(seed) {
    activateTab('#players');
    document.querySelectorAll('.player-item').forEach(function(el) {
        el.classList.remove('player-highlight');
    });
    var target = document.querySelector('.player-item[data-seed="' + seed + '"]');
    if (target) {
        target.classList.add('player-highlight');
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
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
