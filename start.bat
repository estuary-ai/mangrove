@echo off

IF "%ENV_NAME%" == "" (
    SET ENV_NAME=senva
)

echo "Activating Environment:" "%ENV_NAME%"
call conda activate senva

echo "Running Rasa Action server"
call (cd "bot" && rasa "run" "actions")
echo "Running EVA main server"
python "main.py"