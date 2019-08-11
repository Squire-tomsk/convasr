CUDA_VISIBLE_DEVICES=0,1 python3 train.py $@ \
  --verbose --lang ru \
  --model Wav2LetterRu \
  --train-batch-size 80 --val-batch-size 80 \
  --lr 1e-2 --weight-decay 1e-3 --optimizer SGD \
  --train-data-path data/mixed_train.csv \
  --val-data-path data/mixed_val.csv ../sample_ok/sample_ok.convasr.csv \
  --val-iteration-interval 10 \
  --scheduler PolynomialDecayLR --decay-epochs 5 --decay-lr 1e-5 \
  --epochs 1 

#  --train-waveform-transforms 'MixExternalNoise("data/sample_ok.noise.csv", 1.0)' \
#  --val-waveform-transforms 'MixExternalNoise("data/sample_ok.noise.csv", 1.0)' \

#  --noise-data-path data/ru_open_stt_noise_small.csv --noise-level 0.7 \
#  --scheduler MultiStepLR --decay-milestones 10000 30000 40000 80000 --decay-gamma 0.1 \

#  --val-data-path ../open_stt_splits/splits/clean_val.csv ../open_stt_splits/splits/mixed_val.csv ../sample_ok/sample_ok.convasr.csv \
#  --scheduler PolynomialDecayLR --scheduler-decay-epochs 1 --lr-end 1e-5 \
#  --train-data-path /root/convasr/data/mixed_train.csv \
#  --val-data-path /root/convasr/data/mixed_val.csv \
