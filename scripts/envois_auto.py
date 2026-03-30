""": Envois automatiques VLP

on:
  schedule:
    # Tous les jours à 8h00 UTC (10h heure Paris)
    - cron: '0 8 * * *'
  workflow_dispatch:  # Permet de lancer manuellement depuis GitHub

jobs:
  envois:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install supabase requests python-dateutil

      - name: Envois automatiques
        env:
          SUPABASE_URL:         ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          BREVO_API_KEY:        ${{ secrets.BREVO_API_KEY }}
          EMAIL_FROM:           ${{ secrets.EMAIL_FROM }}
          APP_URL:              ${{ secrets.APP_URL }}
        run: python scripts/envois_auto.py
