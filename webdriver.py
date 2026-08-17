"""Backward-compatible launcher for the football results automation CLI.

Install the project first with ``python -m pip install -e .`` and then run:

    python webdriver.py --country England --league "Premier League"
"""

from football_results_scraper.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
