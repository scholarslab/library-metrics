
%.json: %_access.log
	goaccess -f $< --log-format=COMMON --output=$@

%.csv: %.json
	echo "date,visitors,hits" > $@
	cat $< | jq -r '.visitors.data[] | [.data, .visitors.count, .hits.count] | @csv' >> $@

%.summary: %.csv
	csvstat -c visitors,hits $< > $@

install:
	brew install goaccess
	brew install jq
	pip install csvkit

