set -e 

export CUDA_VISIBLE_DEVICES=0,1

ECHOMSK=data/personalno_20000101_20191231.txt.json.gz
CHECKPOINT=best_checkpoints/JasperNetBig_NovoGrad_lr1e-4_wd1e-3_bs1024____long-train_bs1024_step6_430k_checkpoint_epoch247_iter0446576.pt
SAMPLE_RATE=8000

SAMPLE=6000
DATASET=echomsk$SAMPLE
DATASET_ROOT=data/$DATASET
DATASET_AUDIO=$DATASET_ROOT/audio
DATASET_TRANSCRIBE=$DATASET_ROOT/transcribe
DATASET_SUBSET=$DATASET_ROOT/subset
DATASET_CUT=$DATASET_ROOT/cut
DATASET_CUT_JSON=$DATASET_ROOT/cut/cut.json
TRANSCRIBE='--mono --batch-time-padding-multiple 1 --align --skip-processed --max-segment-duration 4.0 --skip-file-longer-than-hours 1.0'
SUBSET='--num-speakers 1 --gap 0.05- --cer 0.0-0.25 --duration 0.5-8.0'
CUT="--dilate 0.025 --sample-rate $SAMPLE_RATE --mono --strip-prefix data/ --add-sub-paths --strip"
TRAIN_TEST_SPLIT='--test-duration-in-hours 0 --val-duration-in-hours 0 --microval-duration-in-hours 10'

#mkdir -p $DATASET_AUDIO
#python3 datasets/echomsk.py -i $ECHOMSK -o $DATASET_AUDIO --sample $SAMPLE
#wget --no-clobber -i $DATASET_AUDIO/audio.txt -P $DATASET_AUDIO
#python3 transcribe.py --checkpoint $CHECKPOINT -i $DATASET_AUDIO -o $DATASET_TRANSCRIBE $TRANSCRIBE
#python3 transcribe.py --checkpoint $CHECKPOINT -i $DATASET_AUDIO -o $DATASET_TRANSCRIBE $TRANSCRIBE

#python3 tools.py subset -i $DATASET_TRANSCRIBE -o $DATASET_SUBSET.json $SUBSET

#rm -r $DATASET_CUT
#python3 tools.py cut -i $DATASET_SUBSET.json -o $DATASET_CUT $CUT

python3 tools.py split -i $DATASET_CUT_JSON -o $DATASET_CUT $TRAIN_TEST_SPLIT
#python3 vis.py audiosample -i $DATASET_CUT/$(basename $DATASET_CUT).json -o $DATASET_CUT.json.html --dataset-root data/
