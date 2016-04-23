all:
	./build.sh

clean:
	./clean.sh
	-rm -f MKVExtractorQt_new.py tmp?.py MKVExtractorQt_2.py MKVRessources_2.qrc

distclean: clean

