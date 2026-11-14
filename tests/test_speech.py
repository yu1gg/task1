import json
from pathlib import Path
import httpx
import pytest
from app.services.speech import SpeechClient, SpeechError


def client(handler, **kwargs):
    return SpeechClient('secret', 'https://example.test/v1', 'asr', 'tts', 'tts:alex', 1, transport=httpx.MockTransport(handler), **kwargs)


def test_protocol(tmp_path):
    source = tmp_path / 'audio.wav'
    source.write_bytes(b'RIFF')
    def handler(request):
        assert request.headers['authorization'] == 'Bearer secret'
        if request.url.path.endswith('transcriptions'):
            assert b'name="model"' in request.content and b'asr' in request.content
            assert b'name="file"' in request.content
            return httpx.Response(200, json={'text': ' hello '})
        assert json.loads(request.content)['response_format'] == 'mp3'
        return httpx.Response(200, content=b'ID3audio', headers={'content-type':'audio/mpeg'})
    adapter = client(handler)
    assert adapter.transcribe(source) == 'hello'
    assert adapter.synthesize('hello') == b'ID3audio'


@pytest.mark.parametrize('status,expected', [(429,3),(503,3),(401,1)])
def test_retry(status,expected,monkeypatch):
    monkeypatch.setattr('app.services.speech.time.sleep',lambda _:None)
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(status,text='secret provider details')
    with pytest.raises(SpeechError) as error:
        client(handler).synthesize('hello')
    assert len(calls)==expected
    assert 'secret' not in str(error.value)


def test_timeout(monkeypatch):
    monkeypatch.setattr('app.services.speech.time.sleep',lambda _:None)
    calls=[]
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout('secret')
    with pytest.raises(SpeechError): client(handler).synthesize('hello')
    assert len(calls)==3


@pytest.mark.parametrize('text',['', ' '*10, 'x'*8001], ids=['empty','blank','long'])
def test_bad_input(text):
    with pytest.raises(SpeechError): client(lambda _:pytest.fail('network')).synthesize(text)


@pytest.mark.parametrize('payload',[b'',b'{}',b'ID3'+b'x'*(5*1024*1024)], ids=['empty','json','oversize'])
def test_invalid_audio(payload):
    with pytest.raises(SpeechError): client(lambda _:httpx.Response(200,content=payload,headers={'content-type':'audio/mpeg'})).synthesize('hello')


def test_missing_key():
    with pytest.raises(SpeechError): SpeechClient('', 'x','a','b','c',1).synthesize('hello')


@pytest.mark.parametrize('value',[None, '', ' '*3, 42, 'x'*8001], ids=['null','empty','blank','number','long'])
def test_invalid_transcript(tmp_path,value):
    source=tmp_path/'x.wav';source.write_bytes(b'a')
    with pytest.raises(SpeechError): client(lambda _:httpx.Response(200,json={'text':value})).transcribe(source)
