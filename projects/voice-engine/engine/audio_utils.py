"""Подготовка аудио перед извлечением тембра: обрезка тишины по краям и
приведение к моно WAV. Работает через pydub/ffmpeg, поэтому принимает
mp3/wav/webm/ogg — что угодно, что умеет читать ffmpeg (в т.ч. запись
из браузера через MediaRecorder)."""

from pydub import AudioSegment
from pydub.silence import detect_nonsilent


def load_and_trim(input_path: str, output_path: str, silence_thresh_db: int = -40) -> str:
    audio = AudioSegment.from_file(input_path).set_channels(1)

    nonsilent = detect_nonsilent(
        audio, min_silence_len=300, silence_thresh=silence_thresh_db
    )
    if nonsilent:
        start = max(0, nonsilent[0][0] - 100)
        end = min(len(audio), nonsilent[-1][1] + 100)
        audio = audio[start:end]

    if len(audio) < 500:
        raise ValueError("В записи почти нет речи — проверьте файл и попробуйте снова.")

    audio.export(output_path, format="wav")
    return output_path
