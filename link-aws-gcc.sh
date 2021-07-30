executables=(addr2line ar as c++filt c89 c99 cc cpp dwp elfedit gcc gcc-ar gcc-nm gcc-ranlib gcov gcov-dump gcov-tool gprof ld ld.bfd ld.gold lto-dump nm objcopy objdump ranlib readelf size strings strip)

for i in "${executables[@]}"
do
	ln -s /usr/bin/$i /usr/bin/gcc10-$i
done
