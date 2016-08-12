
desc 'Generate totals for Geoserver layers.'
task :geoserver do
  sh %{./scripts/geolayers.py --config config.yml --filter '^ESRI' --filter '^MLB'}
end

desc 'Install dependencies.'
task :init do
  sh %{pip install --requirement requirements.txt}
end

