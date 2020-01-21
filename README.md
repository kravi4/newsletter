# newsletter

## Some known issues

before running make sure to pip install pydub and ffprobe

then after that you will have to brew install ffmpeg

you might run into an issue after running it about an error in the brew link step

run brew doctor to diagnose

most likely what you have to do is enter the following:

sudo mkdir -p /usr/local/Frameworks /usr/local/sbin
sudo chown -R $(whoami) /usr/local/Frameworks /usr/local/sbin

then run brew install ffmpeg again and after that run the script
