#! /usr/bin/env python36
#
# Go through MTiles files and build a TMS mapping
#
# Feb-2019, Pat Welch, pat@mousebrains.com
#
import sqlite3
import os
import os.path
import io
import argparse
from tempfile import NamedTemporaryFile
from PIL import Image
from PIL.PngImagePlugin import PngImageFile, PngInfo


def mergeImage(ofn, png, qVerbose):
    if qVerbose:
        print('Merging', ofn)
    with NamedTemporaryFile(delete=False) as ifp:
        ifp.write(png)
        ifp.flush()
        ifp.close()
        im0 = Image.open(ofn).convert('RGBA')
        im1 = Image.open(ifp.name).convert('RGBA')
        im2 = Image.alpha_composite(im0, im1).convert('P')
        im2.save(ofn)
        ifp.close()


parser = argparse.ArgumentParser()
parser.add_argument('mtiles', nargs='+', help='MTiles files to process')
verbose = parser.add_mutually_exclusive_group()
verbose.add_argument('--verbose', action='store_true',
                     help='Output diagnositcs')
verbose.add_argument('--quiet', action='store_true',
                     help='No non-error output')
parser.add_argument('--outdir', default='RNC_ROOT',
                    help='where to write output to')
parser.add_argument('--flip_y', default=True,
                    help='Flip Y axis for non-TMS servers')

args = parser.parse_args()

for fn in args.mtiles:
    if not args.quiet:
        print('Opening', fn)
    with sqlite3.connect(fn) as conn:
        with sqlite3.connect(fn) as conn_meta:
            results = conn.execute('SELECT * FROM tiles;')
            for result in results:  # Walk over rows
                (zoom, column, row, png) = result
                metadata = None
                if zoom <= 7:
                    continue
                metas = conn_meta.execute("SELECT * FROM grid_data WHERE zoom_level = " + str(zoom) + " AND tile_column = " + str(column) + " AND tile_row = " + str(row) + ";")
                for meta in metas:
                    (z, c, r, kn, kj) = meta
                if kj:
                    metadata = kj

                # jayb Y is inverted in TMS (default format for MBTiles)
                if args.flip_y:
                    row = (2 ** zoom) - (1 + row)
                odir = os.path.join(args.outdir, 'Z' + str(zoom), str(row))
                ofn = os.path.join(odir, '{}.png'.format(column))
                if not os.path.isdir(odir):
                    # if args.verbose:
                    #   print('Making directory', odir)
                    os.makedirs(odir)
                if os.path.exists(ofn):
                    mergeImage(ofn, png, args.verbose)
                else:  # Does not exist
                    if args.verbose:
                        print('Saving', ofn, 'length', len(png))
                    if metadata is None:
                        with open(ofn, 'wb') as ofp:
                            ofp.write(png)
                    else:
                        targetImage = Image.open(io.BytesIO(png))
                        #targetImage = Image.frombytes(png)
                        #targetImage.fromstring(png)
                        metainfo = PngInfo()
                        metainfo.add_text("meta", metadata)
                        targetImage.save(ofn, pnginfo=metainfo)
