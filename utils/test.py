from tqdm import tqdm

if __name__=="__main__":
    res = []
    i = 0
    with open('data/librispeech-lm-norm_updated.txt') as f:
        for line in tqdm(f):
            i += 1
            res.append(line.strip())
            print(line.strip())
            if i >= 1000:
                break
    
    #print(res[len(res)-100:len(res)])