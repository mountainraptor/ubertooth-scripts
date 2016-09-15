set timefmt "%s"
set format x "%H:%M:%S"
set xdata time
set datafile separator "|"
set style arrow 1 default
set style arrow 1 nohead
set t x11 persist
plot '< sqlite3 bt-laps.sqlite "SELECT epoch,lap,duration FROM lapTable;"' using 1%900:2:3%900:(0.0) with vectors lw 4 arrow 8
