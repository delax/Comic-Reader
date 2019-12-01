#! python3

""" Browse and read compressed or uncompressed image albums from web browser """

from bottle import Bottle, static_file, request, response, HTTPResponse

from bottle.ext.pystache import view, template

from pathlib import Path

from urllib.parse import quote as url_quote, unquote as url_unquote, urlencode

from zipfile import ZipFile, ZIP_BZIP2

from mimetypes import guess_type

debug_mode = False

app = Bottle()
root_path = Path.cwd()

# home page
@app.route('/')
def welcome():
    return 'Welcome<br/><a href="/browse/">Enter</a>'

@app.route('/static/uncompressed/<titlename:path>')
def send_image(titlename):
    """serve picture from directory, resizing if requested"""
    dir_path = Path(root_path, url_unquote(titlename))
    if dir_path.exists():
        page_num = int(request.query.page or '1')
        resize = bool(int(request.query.resize or '0'))
        
        pages = sorted(filter(is_image_file, dir_path.iterdir()))
        page_num = min(page_num, len(pages))
        page_name = pages[page_num-1].name
        if resize:
            mime, encoding = guess_type(page_name)
            response.set_header('Content-Type', mime)
            with open(str(dir_path.joinpath(page_name)), mode='rb') as imfile:
                body = resize_image(imfile.read())
            return body
        else:
            return static_file(page_name, root=str(dir_path))
        

@app.route('/static/compressed/<titlename:path>')
def send_compressed(titlename):
    """Serve picture from archive, resizing if requested"""
    zip_path = Path(root_path, url_unquote(titlename)).with_suffix('.cbz')
    if zip_path.exists():
        page_num = int(request.query.page or '1')
        resize = bool(int(request.query.resize or '0'))
        with ZipFile(str(zip_path), 'r', ZIP_BZIP2) as zf:
            pages = sorted(filter(is_image_file, zf.namelist()))
            page_num = min(page_num, len(pages))
            page_name = pages[page_num-1]
            mime, encoding = guess_type(page_name)
            response.set_header('Content-Type', mime)
            if resize:
                body = resize_image(zf.read(page_name))
                return body
            else:
                return zf.read(page_name)

@app.route('/browse/')
@app.route('/browse/<dirname:path>')
@view('directories_and_files_lists', layout='basic_layout')
def list_dirs_and_files(dirname=''):
    """List links useful directories and files in 'dirname'"""
    dirpath = Path(url_unquote(dirname))
    file_links = list()
    dir_links = list()
    if dirpath.parent != dirpath:
        dir_links.append({
            'href' : Path('/', 'browse', dirpath.parent),
            'title' : '..',
            })
    for child in sorted((root_path / dirpath).iterdir()):
        if is_useful_dir(child):
            dir_links.append({
                'href' : child.relative_to(root_path).relative_to(dirpath),
                'title' : child.name,
                })
        if is_useful_file(child) or is_image_album(child):
            file_links.append({
                'href' : Path('/', 'view', dirpath, child.name),
                'title' : child.name,
                })

    for link_list in (dir_links, file_links):
        for link in link_list:
            link['href'] = url_quote(link['href'].as_posix())
            if link in dir_links:
                link['href'] += '/'
            
    dir_and_file_links = dict()
    if len(file_links) != 0:
        dir_and_file_links['file_link_list'] = {'link_list' : {'links' : file_links} }
    if len(dir_links) != 0:
        dir_and_file_links['dir_link_list'] = {'link_list' : {'links' : dir_links} }
    return dir_and_file_links

@app.route('/view/<filepath:path>')
@view('reading', layout='basic_layout')
def view_title(filepath):
    """View an album's images"""
    filepath = Path(url_unquote(filepath))
    page_num = int(request.query.page or '1')
    resize = bool(int(request.query.resize or '0'))
    _path_query = '{path!s}?{query!s}' #constant for the url, to make "path/to/comic?query=data"
    
    album_path = root_path / filepath
    if is_useful_file(album_path):
        with ZipFile(str(album_path), 'r', ZIP_BZIP2) as zf:
            number_of_pages = len(list( filter(is_image_file, zf.namelist()) ))
        source = Path('/', 'static', 'compressed', filepath)
    elif is_image_album(album_path):
        number_of_pages = len(list( filter(is_image_file, album_path.iterdir()) ))
        source = Path('/', 'static', 'uncompressed', filepath)
    page_num = min(page_num, number_of_pages)
    return {
        'image' : _path_query.format(
            path = url_quote( source.as_posix() ),
            query = urlencode( {'page' : page_num, 'resize' : int(resize)} )),
        'next' : _path_query.format(
            path = url_quote( filepath.name ),
            query = urlencode( {'page' : min(number_of_pages, page_num+1), 'resize' : int(resize)} )),
        'prev' : _path_query.format(
            path = url_quote( filepath.name ),
            query = urlencode( {'page' : max(1, page_num-1), 'resize' : int(resize)} )),
        'up' : url_quote( Path('/', 'browse', filepath).parent.as_posix() + '/'),
        'resize_link' : {
            'href' : _path_query.format(
                path = url_quote( filepath.name ),
                query = urlencode( {'page' : page_num, 'resize' : int(not resize)} )),
            'title' : 'original' if resize else 'smaller',
            },
        }

def is_useful_file(filepath):
    if not isinstance(filepath, Path):
        filepath = Path(filepath)
    return filepath.is_file() and filepath.suffix == '.cbz'

def is_useful_dir(dirpath):
    if not isinstance(dirpath, Path):
        dirpath = Path(dirpath)
    return dirpath.is_dir() and any(map(
        lambda child: child.is_dir() or is_useful_file(child),
        dirpath.iterdir()
        ))

def is_image_file(filename):
    if isinstance(filename, Path):
        filename = str(filename)
    mimeType = guess_type(filename)[0]
    return mimeType is not None and mimeType.split('/')[0] == 'image'

def is_image_album(dirpath):
    if not isinstance(dirpath, Path):
        dirpath = Path(dirpath)
    return dirpath.is_dir() and any(map(is_image_file, dirpath.iterdir()))

def resize_image(img_bytes, new_width=800):
    from io import BytesIO
    from PIL import Image

    new_body = BytesIO()

    im = Image.open(BytesIO(img_bytes))
    width, height = im.size
    new_height = new_width * height // width
    
    im.resize((new_width, new_height)).save(new_body, im.format)
    return new_body.getvalue()

if __name__ == '__main__':
    from sys import argv
    from os import chdir

    # Force Current Working Dir to file location to allow use of templates
    # Should add file location to template search path instead? 
    chdir(str(Path(__file__).parent))

    if len(argv) > 1:
        p = Path(argv[1])
        if p.is_dir():
            root_path = p
            
    if debug_mode:
        app.run(host='localhost', port=8080, debug=True)
    else:
        app.run(host='0.0.0.0', port=8080, debug=False)
