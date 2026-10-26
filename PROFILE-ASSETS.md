# Profile artwork and data

The banner, badges and technology board are local SVG assets. The banner's Inter and Pixelify glyphs are converted to vector paths, so its typography renders without external font requests. Their SIL Open Font Licenses are included in `assets/licenses/`.

Technology marks come from [Simple Icons](https://github.com/simple-icons/simple-icons), distributed under CC0. Brand marks retain their respective owners' rights. The colors and framing are customized for this profile.

`scripts/update_metrics.py` renders the statistics, language distribution, contribution activity and Codeforces rating charts. It uses Python's standard library, GitHub GraphQL and the public Codeforces API. No external README card service is required.

The [profile charts workflow](.github/workflows/profile-metrics.yml) refreshes the assets daily at 03:37 UTC and can be run manually. Its GitHub token is limited to writing this repository's contents. It runs only on this profile repository; pull requests do not trigger it.

The repository and star counts cover public, original repositories owned by `archon1999`. The language chart aggregates GitHub language bytes across public original repositories, excluding archived repositories; it is not a skill score. GitHub contribution counts may include private/restricted activity counts, as reported by GitHub. No private repository names, URLs, source files or messages are collected.

If GitHub data cannot be retrieved or validated, the refresh fails before replacing existing charts. If Codeforces is temporarily unavailable, the previous rating history is retained. Every chart includes its scope or source; the data snapshot is in `data/metrics.json`.

The Codeforces chart shows rated contest history only. The Yandex Cup and ICPC results in the README are separate achievements with source links.
