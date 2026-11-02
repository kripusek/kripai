import json
import unittest
from unittest.mock import patch
from app import config,generation
from app.network import ToolError

class Stream:
    def __init__(self,text,reason='stop',done=True):self.text,self.reason,self.done=text,reason,done
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):pass
    def iter_lines(self):
        yield 'data: '+json.dumps({'choices':[{'delta':{'content':self.text},'finish_reason':self.reason}]})
        if self.done:yield 'data: [DONE]'

class Client:
    def __init__(self,streams):self.streams=iter(streams);self.calls=[]
    def stream(self,*args,**kwargs):self.calls.append(kwargs['json']);return next(self.streams)

class GenerationTests(unittest.TestCase):
    def test_incomplete_last_line_is_regenerated_without_broken_word(self):
        client=Client([Stream('1. Complete.\n2. Par','length'),Stream('2. Complete.\n')]);snapshots=[]
        with patch.object(generation,'token_count',return_value=100):
            text,reason=generation.generate(client,[],lambda:None,lambda s:None,replace=snapshots.append)
        self.assertEqual(text,'1. Complete.\n2. Complete.\n')
        self.assertEqual(snapshots,['1. Complete.\n'])
    def test_multiple_segments_keep_entire_code_and_original_request(self):
        client=Client([Stream('```python\ndef foo():\n','length'),Stream('    return 1\n```')]);pieces=[]
        messages=[{'role':'user','content':'Napisz funkcję'}]
        with patch.object(generation,'token_count',return_value=1500):
            text,reason=generation.generate(client,messages,lambda:None,pieces.append)
        self.assertEqual(text,'```python\ndef foo():\n    return 1\n```');self.assertEqual(''.join(pieces),text)
        self.assertEqual(reason,'stop');self.assertEqual(client.calls[1]['messages'][0],messages[0])
        self.assertLessEqual(1500+128+client.calls[1]['max_tokens'],config.CONTEXT)
    def test_limit_and_cancel_between_segments(self):
        client=Client([Stream('first','length'),Stream('second','length')])
        with patch.object(generation,'MAX_SEGMENTS',2),patch.object(generation,'token_count',return_value=100):
            text,reason=generation.generate(client,[],lambda:None,lambda s:None)
        self.assertEqual((text,reason),('firstsecond','length'))
        def cancel(segment):raise ToolError('tool_cancelled')
        with patch.object(generation,'token_count',return_value=100):
            with self.assertRaises(ToolError):generation.generate(Client([Stream('first','length')]),[],lambda:None,lambda s:None,cancel)
    def test_broken_continuation_retains_prior_text(self):
        with patch.object(generation,'token_count',return_value=100):
            with self.assertRaises(generation.GenerationInterrupted) as result:
                generation.generate(Client([Stream('first','length'),Stream('partial',done=False)]),[],lambda:None,lambda s:None)
        self.assertEqual(result.exception.text,'firstpartial')
    def test_context_tail_shrinks_and_output_budget_is_dynamic(self):
        sizes=[]
        def count(client,messages):
            sizes.append(len(messages[-2]['content']));return 4000 if sizes[-1]>3000 else 2800
        with patch.object(generation,'token_count',side_effect=count):
            messages,output=generation.continuation(None,[], 'x'*9000)
        self.assertEqual(sizes,[6000,3000]);self.assertEqual(output,1168)
