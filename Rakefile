
desc 'Generate totals for Geoserver layers.'
task :geoserver do
  sh %{./bin/geolayers.py --config config.yml --filter '^ESRI' --filter '^MLB'}
end

namespace :init do
  desc 'Initialize this environment.'
  task :virtualenv do
    sh %{virtualenv .}
    puts "Please load this environment by running 'source bin/activate'."
  end

  desc 'Install dependencies.'
  task :dependencies do
    sh %{pip install --requirement requirements.txt}
  end
end

