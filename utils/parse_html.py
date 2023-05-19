from bs4 import BeautifulSoup
import string
from tqdm import tqdm

def readFile(filename):
    with open(filename) as fp:
        soup = BeautifulSoup(fp, "html.parser")

    return soup

def extract_dialogue(soup):
    fonts = soup.find_all('font')
    res = []
    for font in fonts:
        s = "".join([l for l in str(font.find_next().nextSibling).strip() \
                     if (l not in string.punctuation or l == '\'') and not l.isdigit()]).upper()
        if s.strip():
           res.append(s.strip())

    return res[4:len(res)-1]

def collate_list():
    soup = readFile("apollo11_transcripts.html")
    dialogue = extract_dialogue(soup)
    print('*****DIALOGUE EXTRACTED*****')
    return dialogue

def append_data(filename, filename_new, data_to_append):
    res = []
    with open(filename, 'r') as f:
        for line in tqdm(f):
            res.append(line.strip())

    res.extend(data_to_append)
    res.sort()

    with open(filename_new, 'w') as f:
        for line in tqdm(res):
            f.write(line+'\n')

    print('*****NEW FILE CREATED*****')

if __name__ == "__main__":
    dialogue = collate_list()
    dialogue.sort()

    append_data('data/librispeech-lm-norm.txt', 'data/librispeech-lm-norm_updated.txt', dialogue)