@echo off

echo %1

IF NOT EXIST "filename" (
  echo "STT Model Exists"
) ELSE (
  echo "Downloading STT Model, Please Wait.."
  call download_stt_model.bat
)

IF "%ENV_NAME%" == "" (
    SET ENV_NAME=senva
)

echo "Activating Environment:" "%ENV_NAME%"
call conda activate senva

echo "Running Rasa Action server"
call (cd "bot" && rasa "run" "actions")
echo "Running EVA main server"
python "server.py"