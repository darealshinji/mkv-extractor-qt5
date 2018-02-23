#!/bin/sh

scour --enable-id-stripping \
	--shorten-ids \
	--enable-comment-stripping \
	--disable-embed-rasters \
	--remove-metadata \
	--indent=space \
	-i mkv-extractor-qt5_no_opt.svg \
	-o mkv-extractor-qt5.svg

