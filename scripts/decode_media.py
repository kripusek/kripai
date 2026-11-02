"""Niezaufane dekodery uruchamiane wyłącznie w ograniczonym procesie potomnym."""
import json
import math
import os
from pathlib import Path
import sys
import time
import warnings
from contextlib import closing


def decode(page):
    deadline=time.monotonic()+15
    while not Path('job.ready').exists():
        if time.monotonic()>deadline:raise ValueError('job')
        time.sleep(.02)
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
        resource.setrlimit(resource.RLIMIT_CPU,(15,15))
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS=16_000_000
    warnings.simplefilter('error',Image.DecompressionBombWarning)
    path=Path('original.bin')
    text='';pages=1;truncated=False
    if path.read_bytes()[:5]==b'%PDF-':
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(path) as document:
            pages=len(document)
            if not 1<=pages<=50 or not 1<=page<=pages:raise ValueError('pages')
            with closing(document[page-1]) as pdf_page:
                width,height=pdf_page.get_size()
                if not all(math.isfinite(x) and 0<x<=100000 for x in (width,height)):raise ValueError('size')
                with closing(pdf_page.get_textpage()) as layer:
                    truncated=layer.count_chars()>12000
                    text=layer.get_text_range(0,min(layer.count_chars(),12000))[:12000]
                with closing(pdf_page.render(scale=min(2,1024/max(width,height)),may_draw_forms=False)) as bitmap:
                    image=bitmap.to_pil().convert('RGBA')
        media_type='application/pdf'
    else:
        with Image.open(path) as raw:
            if raw.format not in {'PNG','JPEG'} or getattr(raw,'n_frames',1)!=1 or page!=1:raise ValueError('format')
            if raw.width*raw.height>16_000_000:raise ValueError('pixels')
            media_type='image/png' if raw.format=='PNG' else 'image/jpeg'
            raw.load();image=ImageOps.exif_transpose(raw).convert('RGBA')
    image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
    clean=Image.new('RGB',image.size,'white')
    clean.paste(image,mask=image.getchannel('A'))
    clean.save('preview.png',format='PNG')
    Path('result.json').write_text(json.dumps({'media_type':media_type,'pages':pages,'current_page':page,'text_layer':text,'text_truncated':truncated},ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':
    try:decode(int(sys.argv[1]))
    except Exception:sys.exit(4)
