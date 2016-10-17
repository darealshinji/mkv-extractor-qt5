#!/bin/sh
rm -f mkv-extractor-qt5_optimized*.svg
scour --enable-id-stripping \
	--shorten-ids \
	--enable-comment-stripping \
	--disable-embed-rasters \
	--remove-metadata \
	--indent=none \
	-i mkv-extractor-qt5.svg \
	-o mkv-extractor-qt5_optimized_.svg
tr -d '\n' < mkv-extractor-qt5_optimized_.svg > mkv-extractor-qt5_optimized.svg
rm -f mkv-extractor-qt5_optimized_.svg
