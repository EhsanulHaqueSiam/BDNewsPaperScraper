#!/bin/bash

spiders=(
	BDpratidin
	dailysun
	ittefaq
	kalerKantho
	prothomalo
	bangladesh_today
	thedailystar

)


for spider in "${spiders[@]}"; do
  echo "Running spider: $spider"
  scrapy crawl "$spider" >> logs/"$spider".log 2>&1
done
