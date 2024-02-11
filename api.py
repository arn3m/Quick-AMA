import sys
import os
import csv
import hashlib
from pytube import YouTube
from pydub import AudioSegment
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()
client = OpenAI()

def download_youtube_video(url):
    path='videos'

    # ダウンロードディレクトリの確認と作成
    if not os.path.exists(path):
        os.makedirs(path)

    yt = YouTube(url)
    stream = yt.streams.filter(only_audio=True, file_extension="mp4").first()
    original_title = yt.title.replace(" ", "_").replace("/", "_")
    sha1_hash = hashlib.sha1(url.encode()).hexdigest()
    filename = sha1_hash + '.mp4'
    # ダウンロードと保存
    stream.download(output_path=path, filename=filename)
    return os.path.join(path, filename), sha1_hash, original_title

def transcribe(file, client):

    audio_file= open(file, "rb")
    transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file,
        response_format="text"
    )
    return transcript

def execute_transcription(origin_file, hash):

    file = AudioSegment.from_file(origin_file, "mp4")
    ten_minutes = 10 * 60 * 1000  # 10分をミリ秒単位で
    chunks_dir = "chunk"  # チャンクを保存するディレクトリ
    transcriptions = []

    # チャンクディレクトリの確認と作成
    if not os.path.exists(chunks_dir):
        os.makedirs(chunks_dir)

    for i in range(0, len(file), ten_minutes):
        # ファイルを10分ごとに分割
        chunk = file[i:i + ten_minutes]
        # 連番付きのファイル名
        chunk_file_name = f"{hash}_{i//ten_minutes}.mp4"
        chunk_file_path = os.path.join(chunks_dir, chunk_file_name)  # パスを組み立てる
        chunk.export(chunk_file_path, format="mp4")
        
        # それぞれのチャンクに対してテキスト書き起こしを実行
        transcription = transcribe(chunk_file_path, client)
        transcriptions.append(transcription)
    
    return transcriptions

def main(url):
    # 動画をダウンロード
    origin_file, hash, title = download_youtube_video(url)

    # 'text' ディレクトリを確認し、存在しない場合は作成
    text_dir = 'text'
    if not os.path.exists(text_dir):
        os.makedirs(text_dir)
    
    if origin_file:
        print("動画のダウンロード完了")
        transcriptions = execute_transcription(origin_file, hash)
        if transcriptions:
            print("テキスト書き起こし完了")

            # テキストファイルの完全なパスを構築
            text_file_path = os.path.join(text_dir, title + '.txt')
            # テキストファイルに書き込む
            with open(text_file_path, 'w') as file:
                file.write(title + '\n' + url + '\n\n')
                for transcription in transcriptions:
                    file.write(transcription)  # 書き起こしテキストを書き込む
            print("テキストファイルの保存完了")
        elif transcriptions is None:
            print("テキスト書き起こしに失敗しました")
            sys.exit(1)
    else:
        print("動画ファイルのダウンロードに失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    # コマンドライン引数からCSVファイルのパスを取得
    csv_file_path = sys.argv[1]

    # CSVファイルを開いてURLを読み込む
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            url = row['url']
            main(url)