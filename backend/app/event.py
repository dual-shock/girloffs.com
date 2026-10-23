"""Girloffs 3 seed data: bracket structure, schedule and players.

Only used to fill an empty database. After that the database is the source of truth.
"""

# (number, round, position, slot1, slot2, best_of, third_place)
# A slot is "seed:N", "winner:N" (winner of match N) or "loser:N".
# position = top-to-bottom order inside the round's column.
STRUCTURE = [
    (1, 1, 0, "seed:16", "seed:17", 3, False),
    (2, 1, 1, "seed:13", "seed:20", 3, False),
    (3, 1, 2, "seed:12", "seed:21", 3, False),
    (4, 1, 3, "seed:15", "seed:18", 3, False),
    (5, 1, 4, "seed:14", "seed:19", 3, False),
    (6, 1, 5, "seed:11", "seed:22", 3, False),
    (9, 2, 0, "seed:1", "winner:1", 3, False),
    (7, 2, 1, "seed:8", "seed:9", 3, False),
    (10, 2, 2, "seed:4", "winner:2", 3, False),
    (11, 2, 3, "seed:5", "winner:3", 3, False),
    (12, 2, 4, "seed:2", "winner:4", 3, False),
    (8, 2, 5, "seed:7", "seed:10", 3, False),
    (13, 2, 6, "seed:3", "winner:5", 3, False),
    (14, 2, 7, "seed:6", "winner:6", 3, False),
    (15, 3, 0, "winner:9", "winner:7", 3, False),
    (16, 3, 1, "winner:10", "winner:11", 3, False),
    (17, 3, 2, "winner:12", "winner:8", 3, False),
    (18, 3, 3, "winner:13", "winner:14", 3, False),
    (19, 4, 0, "winner:15", "winner:16", 3, False),
    (20, 4, 1, "winner:17", "winner:18", 3, False),
    (21, 5, 0, "winner:19", "winner:20", 5, False),
    (22, 5, 0, "loser:19", "loser:20", 3, True),
]

# match number -> start time (UTC)
SCHEDULE = {
    1: "2026-10-24T17:00:00Z",
    2: "2026-10-24T17:45:00Z",
    4: "2026-10-24T18:30:00Z",
    6: "2026-10-24T19:15:00Z",
    7: "2026-10-24T20:00:00Z",
    3: "2026-10-24T20:45:00Z",
    12: "2026-10-24T21:30:00Z",
    14: "2026-10-24T22:15:00Z",
    11: "2026-10-24T23:00:00Z",
    5: "2026-10-24T23:45:00Z",
    8: "2026-10-25T00:30:00Z",
    9: "2026-10-25T16:00:00Z",
    10: "2026-10-25T16:45:00Z",
    13: "2026-10-25T17:30:00Z",
    15: "2026-10-25T18:15:00Z",
    16: "2026-10-25T19:00:00Z",
    18: "2026-10-25T19:45:00Z",
    17: "2026-10-25T20:30:00Z",
    19: "2026-10-25T21:15:00Z",
    20: "2026-10-25T22:00:00Z",
    22: "2026-10-25T22:45:00Z",
    21: "2026-10-25T23:30:00Z",
}

# (seed, uuid, mc_name, display_name, pronouns, twitch)
PLAYERS = [
    (1, "64858295eb754646b03caead840391a2", "Casssual", "Casual", "she/her", "casssual_"),
    (2, "3c59ed02bccf4ea3a0f626af7955be91", "tookannn", "tookann", "she/they", "tookann"),
    (3, "dcbe750bdce84bff8e861b69e0343803", "encodey", "encodey", "she/her", "encodeyy"),
    (4, "681679a877ef413c97da63162e835935", "skylewl", "skylewl", "any", "skylewl"),
    (5, "3ccd3947c6d74fd49606c68377c0f655", "amynomaly", "Amy", "she/her", "smeksz"),
    (6, "aa756a8da9784c16b9496f5f5fcaba09", "Czelco", "Czelco", "she/her", "czelco"),
    (7, "1ad3ce1d756144e2b967299789c28030", "ILuvCobblestone", "cobble", "she/it", "iluvcobblestone"),
    (8, "bd276bdda370440a8754989c7faab51a", "CookieAddicts", "CookieAddicts", "she/her", "CookieAddictss"),
    (9, "02833f8a73ca4be0a54aaa48c3fac9a7", "xAurore_", "Aurore", "she/her", "xAurore_"),
    (10, "94f98baeda16495ba745b65afbcc336c", "offlinelotus", "lotus", "he/she", "offlinelotus"),
    (11, "fb3520bced8844608f28d85510f601ed", "Hydrilena", "Hydrilena", "she/her", "hydrilena"),
    (12, "d120be6583ca46c1b9057cf3ff6dfd91", "wmacc", "Mac", "she/her", "wmaccc_"),
    (13, "335578af3f6349ab8dbc4644bdf85a77", "Calixress", "Cali", "she/her", "calixress"),
    (14, "eb86dc19c3f54aefa50ea4bf435a7528", "gdemerald", "emerald", "they/she/it", "gdemerald_"),
    (15, "caba4fdc451b402b9500cdce8549f46b", "Violett_e", "Violet", "she/her", "72violet"),
    (16, "2a19d832269d409f80f669345c5df7cc", "eimiie", "eimiie", "she/her", "eimiiie"),
    (17, "9787ab0ebce6493f8da3676a333a8af2", "InfumeFangirl", "TunaBscuit", "she/they", "tunabscuit"),
    (18, "796d400f64ff4eb09ab223d56dbffbd5", "lishnyan", "Lish", "any", "lishian_"),
    (19, "2125698b0d794c4c99698e39430e65fc", "junesies", "June", "she/her", "junesies"),
    (20, "25b33cc144774af8a85d26bb3f590706", "_sephline", "seph", "she/her", "sephline_"),
    (21, "a821760ca1b8449c87c67efb0b1309a1", "wagahpx", "hpx", "she/her", "hpx374"),
    (22, "2481d626847948c1aad741c0f380143d", "onewiththeskye", "Skye", "she/her", "onewiththeskye"),
]
