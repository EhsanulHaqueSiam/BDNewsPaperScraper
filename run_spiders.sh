#!/bin/bash

spiders=(
  tbdpratidin
  dailysun
  dhakatribune
  ittefaq
  kalerkantho
  prothomalo
  thebangladeshtoday
  thedailystar
)

for spider in "${spiders[@]}"; do
  echo "Running spider: $spider"
  scrapy crawl "$spider"
done

