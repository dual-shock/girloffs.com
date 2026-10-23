export function renderPlayers(state) {
    var rankedIconSrc = document.querySelector('.ranked-icon-src').src;
    var twitchIconSvg = document.querySelector('.twitch-icon-src');
    var container = document.getElementById('players-container');
    container.textContent = '';
    var sorted = state.players.slice().sort(function(a, b) { return a.seed - b.seed; });

    sorted.forEach(function(player) {
        var item = document.createElement('div');
        item.className = 'player-item';
        item.dataset.seed = player.seed;

        var avatar = document.createElement('img');
        avatar.className = 'player-avatar';
        avatar.src = 'https://mc-heads.net/avatar/' + player.mc_name;
        avatar.alt = player.mc_name;

        var info = document.createElement('div');
        info.className = 'player-info';

        var nameEl = document.createElement('div');
        nameEl.className = 'player-info-name';
        nameEl.textContent = player.mc_name;

        var bottom = document.createElement('div');
        bottom.className = 'player-info-bottom';

        var prefName = document.createElement('span');
        prefName.className = 'player-pref-name';
        prefName.textContent = player.display_name;

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
        rankedLink.href = 'https://mcsrranked.com/stats/' + player.mc_name;
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
}
