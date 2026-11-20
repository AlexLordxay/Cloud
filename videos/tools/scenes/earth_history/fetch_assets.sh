#!/bin/bash
# Slow fetch of the chosen Commons files (Wikimedia rate-limits this machine: one file every ~2 min), then searches for
# the shots not yet found. Log: work/earth_history/assets/fetch.log.  commons.py: s = search, g = get + manifest.
cd "$(dirname "$0")"; L=../../work/earth_history/assets/fetch.log; mkdir -p ../../work/earth_history/assets
get() { python3 commons.py g "$@" >> $L 2>&1; echo "--- $2 $?" >> $L; sleep 120; }
get 4 stromatolites "File:Hamelin Pool (Stromatolites) (2051681681).jpg" "Shark Bay, living stromatolites"
get 9 trilobite "File:Fossil Trilobite (with cast).jpg" "trilobite fossil"
get 12b dragonfly "File:Close-Up of Dragonfly on Green Stem in Nature.jpg" "dragonfly close-up"
get 8 charnia "File:Charnia masoni.jpg" "Ediacaran fossil Charnia"
get 12a horsetail "File:Equisetum sylvaticum RF.jpg" "horsetail"
get 5 karijini "File:Karijini National Park (2051691003).jpg" "banded iron formation gorge, Karijini"
for q in "dinosaur skeleton museum" "Himalaya from the International Space Station" "ISS night Earth city lights video" "lava flow Kilauea video" "crocodile" "chimpanzee" "zircon crystal Jack Hills" "coal fossil fern" "Putorana plateau" "coelacanth"; do
  echo "=== $q" >> $L; python3 commons.py s "$q" 8 >> $L 2>&1; sleep 90
done
echo FINISHED >> $L
