if [ -z ${ENV_NAME+x} ];
then ENV_NAME="senva";
fi

echo "Activating Environment:" $ENV_NAME
eval "$(conda shell.bash hook)"
conda activate $ENV_NAME

echo "Running Rasa Action server"
cd bot && rasa run actions &
echo "Running EVA main server"
python main.py   