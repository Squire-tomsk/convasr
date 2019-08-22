CUDA_VISIBLE_DEVICES=0,1 python3 train.py $@ \
  --checkpoint data/checkpoint_epoch04_iter0124135.pt \
  --val-batch-size 32 --val-data-path  ../sample_ok/sample_ok.convasr.csv \
  --decoder BeamSearchDecoder --beam-width 2000 --lm charlm/chats_06_noprune_char.binary #chats_03_prune.binary #

#  --checkpoint data/experiments/Wav2LetterRu_SGD_lr1e-2_wd1e-3_bs80__8khz/checkpoint_epoch01_iter0025000.pt \

#  --val-feature-transform SpecLowPass 4000 16000

#  --val-batch-size 32 --val-data-path data/clean_val.csv ../sample_ok/sample_ok.convasr.csv data/sample_ok.convasr.lowpass.csv data/clean_val.lowpass.csv #\


#  --checkpoint data/experiments/Wav2LetterRu_SGD_lr1e-2_wd1e-3_bs80_augSOXSP0.3/checkpoint_epoch00_iter0012500.pt \


#--val-batch-size 64 --val-data-path ../sample_ok/sample_ok.convasr.csv \

# --decoder BeamSearchDecoder --beam-width 20000 --lm chats_03_prune.binary #chats.binary #data/ru_wiyalen_no_punkt.arpa.binary

#  --val-waveform-transform MixExternalNoise --val-waveform-transform-prob 1 --val-waveform-transform-args data/ru_open_stt_noise_small.csv --val-waveform-transform-debug-dir data/debug_aug \

#  --val-waveform-transform MixExternalNoise --val-waveform-transform-prob 1 --val-waveform-transform-args data/sample_ok.noise.csv --val-waveform-transform-debug-dir data/debug_aug \

#  --val-waveform-transform AddWhiteNoise --val-waveform-transform-prob nan \

#  --val-waveform-transform SOXAWN --val-waveform-transform-debug-dir data/debug_aug \



#  data/adapted.csv 
#  --val-batch-size 40 --val-data-path  ../open_stt_splits/splits/clean_val.csv ../open_stt_splits/splits/mixed_val.csv ../sample_ok/sample_ok.convasr.csv \
#  --checkpoint model_checkpoint_0027_epoch_02.model.pt \
#  --noise-data-path data/ru_open_stt_noise_small.csv --noise-level 0.5 \
