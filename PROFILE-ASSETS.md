# Profile artwork and data

## Artwork

The NB banner, achievement cards, product diagrams and technology board are local, theme-aware SVG assets. Static labels use outlined Inter and JetBrains Mono; large headings include a few Alpha Lyrae glyphs. Typography renders consistently without external font requests. Live platform counters remain text so the daily workflow can refresh them. The SIL Open Font Licenses are included in `assets/licenses/`.

Achievement cards use a trophy, the Codeforces bars and the original KEP mark. Dark and light variants share the same dimensions and hierarchy. The Codeforces badge records the peak rating; the history chart provides dated rating data.

Technology marks come from [Simple Icons](https://github.com/simple-icons/simple-icons), distributed under CC0. Product marks and company names retain their respective owners’ rights. The illustrations describe engineering boundaries; they are not application screenshots.

## Statistics tools

- [GitHub Readme Stats](https://github.com/stats-organization/github-readme-stats) produces the statistics and language cards through its [GitHub Action](https://github.com/stats-organization/github-readme-stats-action), with core version 2.2.0 pinned. Languages use source-byte weighting, not a skill score.
- [GitHub Readme Streak Stats](https://github.com/DenverCoder1/github-readme-streak-stats) produces total, current and longest contribution streaks in `Asia/Tashkent`.
- `scripts/update_metrics.py` produces the contribution calendar and Codeforces history using GitHub GraphQL and the public Codeforces API. Calendar levels come directly from GitHub’s `contributionLevel`.
- `scripts/update_products.py` retrieves registered users, visible problems, contests and submissions from the [KEP.uz public statistics API](https://kep.uz/api/landing-page-statistics). The source, observation time and counter meanings are recorded in `data/products.json`.

The [workflow](.github/workflows/profile-metrics.yml) refreshes twelve cards daily at 03:37 UTC (08:37 in Tashkent) and can run manually. Actions are pinned to commit SHAs. It uses the repository’s `GITHUB_TOKEN`; no personal access token or extra secret is required. Cards are committed locally, so opening the profile does not depend on a public statistics-image service.

## Data scope and failure handling

GitHub Readme Stats uses public repositories visible to the workflow token. Commit, issue, pull-request and contributed-repository totals have distinct API scopes and need not equal the contribution calendar. Language percentages measure source bytes in repositories processed by the tool.

The custom snapshot in `data/metrics.json` separately enumerates public, original repositories owned by `archon1999`; its language inventory excludes archived repositories. Calendar and streak counts can include aggregate private activity exposed by GitHub. No private repository names, URLs, source files or messages are collected.

GitHub retrieval or card-validation failure stops replacement charts from being committed. If Codeforces or KEP.uz is unavailable, the corresponding previous data, cards and observation date are retained. KEP counters are checked for numeric type and range; tests cover malformed counters, failed retrieval and the Tashkent date boundary.

The Cafe Postcode 200+ branch figure is the maintainer’s product operating count. It is not a live GitHub statistic or a deployment count for one repository. Yandex Cup, ICPC and other competition results have separate links in the README.
