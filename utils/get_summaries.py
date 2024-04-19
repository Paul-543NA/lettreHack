from subprocess import run

from api import summarize


run("""
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/facebook/bart-large-cnn
cd bart-large-cnn
rm -f model.safetensors
wget 'https://huggingface.co/facebook/bart-large-cnn/resolve/main/model.safetensors'
""", shell=True)

data_path = "../data/single-page-letters.csv"
summaries = summarize(data_path, model_path="bart-large-cnn", chunk_size=1024, max_length=75)
read_csv(data_path).assign(Summary=summaries[1:]).to_csv(data_path, index=None)
