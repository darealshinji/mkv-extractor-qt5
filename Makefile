all:
	./build.sh && wget -nv -c -O BDSup2Sub.jar https://raw.githubusercontent.com/wiki/mjuhasz/BDSup2Sub/downloads/BDSup2Sub.jar

clean:
	./clean.sh

distclean: clean
	-rm -f BDSup2Sub.jar

