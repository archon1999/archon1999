# Profile artwork and data

The banner, badges and technology board are local SVG assets. The banner’s Inter and Pixelify glyphs are converted to vector paths, so its typography renders without external font requests. Their SIL Open Font Licenses are included in `assets/licenses/`.

Technology marks come from [Simple Icons](https://github.com/simple-icons/simple-icons), distributed under CC0. Brand marks retain their respective owners’ rights.

## Statistics tools

- [GitHub Readme Stats](https://github.com/stats-organization/github-readme-stats) renders the statistics and top-language cards through its [GitHub Action](https://github.com/stats-organization/github-readme-stats-action), with core version 2.2.0 pinned. The top-language card uses byte weighting (`size_weight=1`, `count_weight=0`), not a skill score.
- [GitHub Readme Streak Stats](https://github.com/DenverCoder1/github-readme-streak-stats) renders total, current and longest contribution streaks. Dates use `Asia/Tashkent`.
- `scripts/update_metrics.py` renders the daily contribution calendar and Codeforces rating history using GitHub GraphQL and the public Codeforces API. Calendar cell levels come directly from GitHub’s `contributionLevel`, rather than locally estimated thresholds.

These are community tools that use GitHub data. Cards are generated in Actions and committed as local SVGs; viewing this profile does not depend on a public statistics-card endpoint. Dark and light variants use GitHub’s interface and contribution-calendar colors. Codeforces history uses a purple rating line.

The [profile charts workflow](.github/workflows/profile-metrics.yml) refreshes all ten cards daily at 03:37 UTC (08:37 in Tashkent) and can be run manually. Third-party actions are pinned to commit SHAs. It uses this repository’s `GITHUB_TOKEN`, with repository-content write access for committing generated assets. No personal access token or extra secret is required.

## Data scope

GitHub Readme Stats uses the public repositories visible to the workflow token. Its commit, issue, pull-request and contributed-repository totals have their own scopes and are not the same metric as the contribution calendar. Language percentages measure GitHub-reported source bytes across repositories processed by the tool.

The custom snapshot in `data/metrics.json` separately enumerates public, original repositories owned by `archon1999`; its language-byte inventory excludes archived repositories. It is retained for the calendar and source transparency, and is not substituted for the tool-generated cards.

Calendar and streak counts may include restricted/private activity counts exposed by GitHub. No private repository names, URLs, source files or messages are collected. GitHub and streak-tool totals can differ because their time ranges and API visibility differ.

If GitHub data cannot be retrieved or validated, the refresh fails before publishing replacement cards. The statistics action is configured to fail on data-fetch errors, and all ten SVGs are checked before committing. If Codeforces is temporarily unavailable, the previous rating history and its check date are retained.

The Codeforces chart shows rated contest history only. Yandex Cup and ICPC results in the README are separate achievements with source links.
