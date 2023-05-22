cd models/ds-model
mkdir optimal_models && cd optimal_models
wget https://www.dropbox.com/s/cvm55q92kif7q18/lm_unopt_senva.zip?dl=1 -O lm_unopt_senva_small.zip
wget https://www.dropbox.com/s/jaw5f3zfnjugxgb/lm_unopt_commands_final.zip?dl=1 -O lm_unopt_commands_large.zip
wget https://www.dropbox.com/s/kv5d8vrlkl1e8zs/lm_unopt_st_final.zip?dl=1 -O lm_unopt_transcript_senva_large.zip

cat <<EOF > optimal_hyperparams.txt
Commands Large: parameters: {'lm_alpha': 2.504105614229454, 'lm_beta': 2.349839144592003}, score: 0.3016157989228007
Transcripts and Commands Large: parameters: {'lm_alpha': 2.3464642590639166, 'lm_beta': 1.0261397277723683}, score: 0.33213644524236985
Baseline Parameters: {'lm_alpha': 0.931289039105002, 'lm_beta': 1.1834137581510284}
EOF