#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)
import os
import sys

from docopt import docopt
from path import path

from gutenberg import logger
from gutenberg.database import setup_database
from gutenberg.rdf import setup_rdf_folder, parse_and_fill
from gutenberg.download import download_all_books
from gutenberg.export import export_all_books
from gutenberg.zim import build_zimfile
from gutenberg.checkdeps import check_dependencies


help = ("""Usage: dump-gutenberg.py [-k] [-l LANGS] [-f FORMATS] """
        """[-r RDF_FOLDER] [-m URL_MIRROR] [-d CACHE_PATH] [-e STATIC_PATH] [-z ZIM_PATH] [-u RDF_URL] [-b BOOKS] """
        """[--prepare] [--parse] [--download] [--export] [--zim] [--complete]

-h --help                       Display this help message
-k --keep-db                    Do not wipe the DB during parse stage

-l --languages=<list>           Comma-separated list of lang codes to filter export to (preferably ISO 639-1, else ISO 639-3)
-f --formats=<list>             Comma-separated list of formats to filter export to (epub, html, pdf, all)

-m --mirror=<url>               Use URL as base for all downloads.
-r --rdf-folder=<folder>        Don't download rdf-files.tar.bz2 and use extracted folder instead
-e --static-folder=<folder>     Use-as/Write-to this folder static HTML
-z --zim-file=<file>            Write ZIM into this file path
-d --dl-folder=<folder>         Folder to use/write-to downloaded ebooks
-u --rdf-url=<url>              Alternative rdf-files.tar.bz2 URL
-b --books=<ids>                Execute the processes for specific books, separated by commas, or dashes for intervals

-x --zim-title=<title>          Custom title for the ZIM file
-q --zim-desc=<desc>            Custom description for the ZIM file

--check                         Check dependencies
--prepare                       Download & extract rdf-files.tar.bz2
--parse                         Parse all RDF files and fill-up the DB
--download                      Download ebooks based on filters
--export                        Export downloaded content to zim-friendly static HTML
--zim                           Create a ZIM file

This script is used to produce a ZIM file (and any intermediate state)
of Gutenberg repository using a mirror.""")


def main(arguments):

    # actions constants
    DO_PREPARE = arguments.get('--prepare', False)
    DO_PARSE = arguments.get('--parse', False)
    DO_DOWNLOAD = arguments.get('--download', False)
    DO_EXPORT = arguments.get('--export', False)
    DO_ZIM = arguments.get('--zim', False)
    DO_CHECKDEPS = arguments.get('--check', False)
    COMPLETE_DUMP = arguments.get('--complete', False)

    URL_MIRROR = arguments.get('--mirror') or 'http://zimfarm.kiwix.org/gutenberg'
    RDF_FOLDER = arguments.get('--rdf-folder') or os.path.join('rdf-files')
    STATIC_FOLDER = arguments.get('--static-folder') or os.path.join('static')
    ZIM_FILE = arguments.get('--zim-file')
    WIPE_DB = not arguments.get('--keep-db') or False
    RDF_URL = arguments.get('--rdf-url') or 'http://www.gutenberg.org/cache/epub/feeds/rdf-files.tar.bz2'
    DL_CACHE = arguments.get('--dl-folder') or os.path.join('dl-cache')
    BOOKS = arguments.get('--books') or ''
    ZTITLE = arguments.get('--zim-title')
    ZDESC = arguments.get('--zim-desc')

    # create tmp dir
    path('tmp').mkdir_p()

    LANGUAGES = [x.strip().lower()
                 for x in (arguments.get('--languages') or '').split(',')
                 if x.strip()]
    # special shortcuts for "all"
    if arguments.get('--formats') in ['all', None]:
        FORMATS = ['epub', 'pdf']
    else:
        FORMATS = [x.strip().lower()
                   for x in (arguments.get('--formats') or '').split(',')
                   if x.strip()]

    try:
        BOOKS = [bid for bid in BOOKS.split(',')]
        f = lambda x: map(int, [i for i in x.split('-') if i.isdigit()])
        books = []
        for i in BOOKS:
            blst = f(i)
            if len(blst) > 1:
                blst = range(blst[0], blst[1]+1)
            books.extend(blst)
        BOOKS = list(set(books))
    except Exception as e:
        logger.error(e)
        BOOKS = []

    # no arguments, default to --complete
    if not (DO_PREPARE + DO_PARSE + DO_DOWNLOAD + DO_EXPORT + DO_ZIM):
        COMPLETE_DUMP = True

    if COMPLETE_DUMP:
        DO_CHECKDEPS = DO_PREPARE = DO_PARSE = \
            DO_DOWNLOAD = DO_EXPORT = DO_ZIM = True

    if DO_CHECKDEPS:
        logger.info("CHECKING for dependencies on the system")
        if not check_dependencies()[0]:
            logger.error("Exiting...")
            sys.exit(1)

    if DO_PREPARE:
        logger.info("PREPARING rdf-files cache from {}".format(RDF_URL))
        setup_rdf_folder(rdf_url=RDF_URL, rdf_path=RDF_FOLDER)

    if DO_PARSE:
        logger.info("PARSING rdf-files in {}".format(RDF_FOLDER))
        setup_database(wipe=WIPE_DB)
        parse_and_fill(rdf_path=RDF_FOLDER, only_books=BOOKS)

    if DO_DOWNLOAD:
        logger.info("DOWNLOADING ebooks from mirror using filters")
        download_all_books(url_mirror=URL_MIRROR,
                           download_cache=DL_CACHE,
                           languages=LANGUAGES,
                           formats=FORMATS,
                           only_books=BOOKS)

    if DO_EXPORT:
        logger.info("EXPORTING ebooks to static folder (and JSON)")
        export_all_books(static_folder=STATIC_FOLDER,
                         download_cache=DL_CACHE,
                         languages=LANGUAGES,
                         formats=FORMATS,
                         only_books=BOOKS)

    if DO_ZIM:
        if not check_dependencies()[1]:
            logger.error("You don't have zimwriterfs installed.")
            sys.exit(1)
        logger.info("BUILDING ZIM off static folder {}".format(STATIC_FOLDER))
        build_zimfile(static_folder=STATIC_FOLDER, zim_path=ZIM_FILE,
                      languages=LANGUAGES, formats=FORMATS,
                      only_books=BOOKS,
                      title=ZTITLE, description=ZDESC)

if __name__ == '__main__':
    main(docopt(help, version=0.1))
