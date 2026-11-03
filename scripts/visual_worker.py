"""Przypięty encoder CPU; pliki IPC wyłącznie w prywatnym folderze zadania."""
import io
import json
import os
from pathlib import Path
import site
import sys
import time


def main(runtime):
    deadline=time.monotonic()+15
    while not Path('job.ready').is_file():
        if time.monotonic()>deadline:raise ValueError('visual_start_timeout')
        time.sleep(.02)
    deps=runtime/'deps'
    sys.path.insert(0,str(deps));site.addsitedir(str(deps))
    os.environ['TOKENIZERS_PARALLELISM']='false'
    import numpy as np
    import onnxruntime as ort
    from PIL import Image
    from tokenizers import Tokenizer
    Image.MAX_IMAGE_PIXELS=1024**2
    assets=runtime/'assets'
    tokenizer=Tokenizer.from_file(str(assets/'tokenizer.json'))
    tokenizer.no_truncation();tokenizer.no_padding()
    options=ort.SessionOptions()
    options.intra_op_num_threads=2;options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    models={kind:ort.InferenceSession(str(assets/(kind+'_model_quantized.onnx')),options,
                                    providers=['CPUExecutionProvider']) for kind in ('text','vision')}
    Path('ready.tmp').write_bytes(b'{"ready":true}')
    Path('ready.tmp').replace('ready.json')
    while True:
        if not Path('request.json').is_file():time.sleep(.02);continue
        try:
            request=json.loads(Path('request.json').read_text(encoding='utf-8'))
            if request.get('action')=='text':
                text=request.get('text')
                if not isinstance(text,str) or not 1<=len(text.strip())<=500:raise ValueError('visual_query_invalid')
                ids=tokenizer.encode(text.strip()).ids
                # Eksport tokenizera może obcinać tekst; wyżej jawnie to wyłączamy.
                if len(ids)>64:raise ValueError('visual_query_too_large')
                ids=ids+[0]*(64-len(ids))
                vector=models['text'].run(['pooler_output'],{'input_ids':np.asarray([ids],dtype=np.int64)})[0][0]
            elif request.get('action')=='image':
                data=Path('image.png').read_bytes()
                if not 1<=len(data)<=4*1024**2:raise ValueError('visual_image_invalid')
                with Image.open(io.BytesIO(data)) as image:
                    if image.format!='PNG' or getattr(image,'n_frames',1)!=1 or image.width*image.height>1024**2:raise ValueError('visual_image_invalid')
                    image.load()
                    pixels=np.asarray(image.convert('RGB').resize((224,224),Image.Resampling.BILINEAR),dtype=np.float32)
                pixels=((pixels/255.-.5)/.5).transpose(2,0,1)[None,...]
                vector=models['vision'].run(['pooler_output'],{'pixel_values':pixels})[0][0]
            else:raise ValueError('visual_request_invalid')
            vector=np.asarray(vector,dtype=np.float32)
            if vector.shape!=(768,) or not np.isfinite(vector).all():raise ValueError('visual_vector_invalid')
            norm=float(np.linalg.norm(vector))
            if not norm>0:raise ValueError('visual_vector_invalid')
            response={'embedding':(vector/norm).tolist()}
        except ValueError as exc:
            code=str(exc)
            response={'error':code if code in {'visual_query_invalid','visual_query_too_large','visual_image_invalid','visual_vector_invalid','visual_request_invalid'} else 'visual_encode_failed'}
        except Exception:response={'error':'visual_encode_failed'}
        Path('request.json').unlink()
        Path('response.tmp').write_bytes(json.dumps(response).encode())
        Path('response.tmp').replace('response.json')


if __name__=='__main__':
    try:main(Path(sys.argv[1]))
    except Exception:sys.exit(4)
