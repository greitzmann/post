# -*- coding: utf-8 -*-

import numpy as np
import torch
from torch.nn.utils.rnn import pad_sequence


class Corpus(object):
    SOS = '<SOS>'
    EOS = '<EOS>'
    UNK = '<UNK>'

    def __init__(self, words, tags):
        self.words = words
        self.tags = tags

        self.wdict = {w: i for i, w in enumerate(self.words)}
        self.tdict = {t: i for i, t in enumerate(self.tags)}
        self.si = self.wdict[self.SOS]
        self.ei = self.wdict[self.EOS]
        self.ui = self.wdict[self.UNK]
        self.nw = len(self.words)
        self.nt = len(self.tags)

    def load(self, fdata, window=5):
        x, y, lens = [], [], []
        half = window // 2
        # 句子按照长度从大到小有序
        sentences = sorted(self.preprocess(fdata),
                           key=lambda x: len(x[0]),
                           reverse=True)
        for wordseq, tagseq in sentences:
            wiseq = [self.wdict.get(w, self.ui) for w in wordseq]
            wiseq = [self.si] * half + wiseq + [self.ei] * half
            tiseq = [self.tdict[t] for t in tagseq]
            x.append(torch.tensor([wiseq[i:i + window]
                                   for i in range(len(tiseq))],
                                  dtype=torch.long))
            y.append(torch.tensor([ti for ti in tiseq], dtype=torch.long))
            lens.append(len(tiseq))
        x = pad_sequence(x, batch_first=True)
        y = pad_sequence(y, batch_first=True)
        lens = torch.tensor(lens)
        return x, y, lens

    def size(self):
        return self.nw - 3, self.nt

    @staticmethod
    def preprocess(fdata):
        start = 0
        sentences = []
        with open(fdata, 'r') as train:
            lines = [line for line in train]
        for i, line in enumerate(lines):
            if len(lines[i]) <= 1:
                splits = [l.split()[1:4:2] for l in lines[start:i]]
                wordseq, tagseq = zip(*splits)
                start = i + 1
                while start < len(lines) and len(lines[start]) <= 1:
                    start += 1
                sentences.append((wordseq, tagseq))
        return sentences

    @staticmethod
    def get_embed(fembed):
        with open(fembed, 'r') as f:
            lines = [line for line in f]
        splits = [line.split() for line in lines]
        words, embed = zip(*[
            (split[0], list(map(float, split[1:]))) for split in splits
        ])
        words = list(words)
        embed = torch.FloatTensor(embed)
        return words, embed

    @staticmethod
    def parse(sentences):
        wordseqs, tagseqs = zip(*sentences)
        words = sorted(set(np.hstack(wordseqs)))
        tags = sorted(set(np.hstack(tagseqs)))
        return words, tags