var featuredSeed = 1;
var lastState = null;

export function renderPlayers(state) {
    lastState = state;
    var rankedIconSrc = document.querySelector('.ranked-icon-src').src;
    var twitchIconSvg = document.querySelector('.twitch-icon-src');
    var container = document.getElementById('players-container');
    container.textContent = '';
    var sorted = state.players.slice().sort(function(a, b) { return a.seed - b.seed; });
    var featured = sorted.find(function(p) { return p.seed === featuredSeed; }) || sorted[0];
    if (!featured) return;

    var featuredItem = buildItem(featured, rankedIconSrc, twitchIconSvg);
    featuredItem.classList.add('player-featured');
    container.appendChild(featuredItem);
    container.appendChild(buildRender(featured));

    sorted.forEach(function(player) {
        if (player !== featured) container.appendChild(buildItem(player, rankedIconSrc, twitchIconSvg));
    });
}

// the featured player takes the left slot; whoever was there goes back to their seed position in the list
export function featurePlayer(seed) {
    featuredSeed = seed;
    if (lastState) renderPlayers(lastState);
    document.getElementById('players-container').scrollTo({ top: 0, behavior: 'smooth' });
}

function buildRender(player) {
    return buildPicture('assets/players/', player, 'player-render');
}

function buildPicture(dir, player, className) {
    var picture = document.createElement('picture');
    picture.className = className;

    var source = document.createElement('source');
    source.type = 'image/avif';
    source.srcset = dir + player.seed + '.avif';

    var img = document.createElement('img');
    img.src = dir + player.seed + '.webp';
    img.alt = player.mc_name;
    img.addEventListener('error', function() { img.style.visibility = 'hidden'; });

    picture.appendChild(source);
    picture.appendChild(img);
    return picture;
}

function buildItem(player, rankedIconSrc, twitchIconSvg) {
    var item = document.createElement('div');
    item.className = 'player-item';
    item.dataset.seed = player.seed;

    // the seed sits on the head like a Minecraft item-stack count
    var head = document.createElement('div');
    head.className = 'player-head';

    var avatar = buildPicture('assets/heads/', player, 'player-avatar');

    var seedEl = document.createElement('span');
    seedEl.className = 'player-item-seed';
    seedEl.textContent = player.seed;

    head.appendChild(avatar);
    head.appendChild(seedEl);

    var info = document.createElement('div');
    info.className = 'player-info';

    var top = document.createElement('div');
    top.className = 'player-info-top';

    var nameEl = document.createElement('span');
    nameEl.className = 'player-info-name';
    nameEl.textContent = player.display_name;

    var pronouns = document.createElement('span');
    pronouns.className = 'player-pronouns';
    pronouns.textContent = player.pronouns;

    var mcName = document.createElement('div');
    mcName.className = 'player-mc-name';
    mcName.textContent = player.mc_name;

    top.appendChild(nameEl);
    top.appendChild(pronouns);
    info.appendChild(top);
    info.appendChild(mcName);

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

    var content = document.createElement('div');
    content.className = 'player-item-content';
    var links = document.createElement('div');
    links.className = 'player-links';
    links.appendChild(twitchLink);
    links.appendChild(rankedLink);

    content.appendChild(head);
    content.appendChild(info);
    content.appendChild(links);

    item.appendChild(content);

    content.addEventListener('click', function(e) {
        if (e.target.closest('a')) return;
        if (player.seed !== featuredSeed) featurePlayer(player.seed);
    });
    return item;
}
