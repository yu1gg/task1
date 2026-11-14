import json
import subprocess
import wave
from pathlib import Path
import pytest
from app.services import audio


@pytest.mark.parametrize('name',['../x', '/tmp/x', 'C:\\x', '..\\x', 'https://evil/x', ''])
def test_paths(name,tmp_path,monkeypatch):
    monkeypatch.setattr(audio.settings,'data_dir',tmp_path)
    with pytest.raises(audio.AudioError): audio.resolve_media(name)


def test_media_root(tmp_path,monkeypatch):
    monkeypatch.setattr(audio.settings,'data_dir',tmp_path)
    assert audio.resolve_media('safe.wav')==tmp_path/'interview_audio'/'safe.wav'
    assert audio.media_root().is_dir()


def fake_runner(duration=1,streams=None):
    def run(args,**kwargs):
        assert kwargs.get('shell',False) is False
        assert kwargs['timeout']<=30
        if '-show_streams' in args:
            return subprocess.CompletedProcess(args,0,json.dumps({'streams':streams if streams is not None else [{'codec_type':'audio'}]}),'')
        assert '-nostdin' in args and args[args.index('-protocol_whitelist')+1]=='file,pipe'
        assert args[args.index('-t')+1]=='91'
        with wave.open(str(args[-1]),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(b'\0\0'*int(duration*16000))
        return subprocess.CompletedProcess(args,0,'','')
    return run


def test_normalize(tmp_path,monkeypatch):
    source=tmp_path/'browser.webm';source.write_bytes(b'input')
    monkeypatch.setattr(audio,'check_tools',lambda:True)
    monkeypatch.setattr(audio.subprocess,'run',fake_runner())
    destination=tmp_path/'out.wav'
    audio.normalize_audio(source,destination)
    with wave.open(str(destination)) as wav: assert wav.getframerate()==16000


@pytest.mark.parametrize('duration,streams',[(91,None),(1,[]),(1,[{'codec_type':'video'},{'codec_type':'audio'}])])
def test_reject_audio(tmp_path,monkeypatch,duration,streams):
    source=tmp_path/'input';source.write_bytes(b'input')
    monkeypatch.setattr(audio,'check_tools',lambda:True)
    monkeypatch.setattr(audio.subprocess,'run',fake_runner(duration,streams))
    destination=tmp_path/'out.wav'
    with pytest.raises(audio.AudioError): audio.normalize_audio(source,destination)
    assert not destination.exists()


def test_missing_tools(tmp_path,monkeypatch):
    source=tmp_path/'input';source.write_bytes(b'input')
    monkeypatch.setattr(audio,'check_tools',lambda:False)
    with pytest.raises(audio.AudioError,match='ffmpeg'): audio.normalize_audio(source,tmp_path/'out')

@pytest.mark.parametrize('failure',[subprocess.TimeoutExpired('ffmpeg',30), subprocess.CalledProcessError(1,'ffmpeg',stderr='private path'), FileNotFoundError('private path')],ids=['timeout','decode','missing'])
def test_failed_process_cleanup(tmp_path,monkeypatch,failure):
    source=tmp_path/'input';source.write_bytes(b'input')
    destination=tmp_path/'out.wav'
    monkeypatch.setattr(audio,'check_tools',lambda:True)
    def run(*args,**kwargs):
        destination.write_bytes(b'partial')
        raise failure
    monkeypatch.setattr(audio.subprocess,'run',run)
    with pytest.raises(audio.AudioError) as error: audio.normalize_audio(source,destination)
    assert 'private' not in str(error.value)
    assert not destination.exists()


def test_oversize_input(tmp_path,monkeypatch):
    source=tmp_path/'input'
    with source.open('wb') as output: output.truncate(20*1024*1024+1)
    monkeypatch.setattr(audio,'check_tools',lambda:True)
    monkeypatch.setattr(audio.subprocess,'run',lambda *a,**k:pytest.fail('must reject before process'))
    with pytest.raises(audio.AudioError): audio.normalize_audio(source,tmp_path/'out')


def test_preserve_existing_output(tmp_path):
    destination=tmp_path/'out.wav';destination.write_bytes(b'existing')
    with pytest.raises(audio.AudioError): audio.normalize_audio(tmp_path/'input',destination)
    assert destination.read_bytes()==b'existing'

@pytest.mark.parametrize('streams',[{},'wrong',[None]],ids=['mapping','string','null-stream'])
def test_invalid_probe_output(tmp_path,monkeypatch,streams):
    source=tmp_path/'input';source.write_bytes(b'input')
    monkeypatch.setattr(audio,'check_tools',lambda:True)
    monkeypatch.setattr(audio.subprocess,'run',fake_runner(streams=streams))
    with pytest.raises(audio.AudioError): audio.normalize_audio(source,tmp_path/'out')
