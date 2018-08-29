# -*- coding: utf-8 -*-

import argparse
from datetime import datetime, timedelta

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

import config
from corpus import Corpus
from models import BPNN, LSTM, LSTM_CHAR, Network


if __name__ == '__main__':
    # 解析命令参数
    parser = argparse.ArgumentParser(
        description='Create several models for POS Tagging.'
    )
    parser.add_argument('--model', '-m', default='default',
                        dest='model', choices=['bpnn', 'lstm', 'lstm_char'],
                        help='choose the model for POS Tagging')
    parser.add_argument('--crf', '-c', action='store_true', default=False,
                        dest='crf', help='use crf')
    parser.add_argument('--prob', action='store', default=0.5, type=float,
                        dest='prob', help='set the prob of dropout')
    parser.add_argument('--batch_size', action='store', default=50, type=int,
                        dest='batch_size', help='set the size of batch')
    parser.add_argument('--epochs', action='store', default=100, type=int,
                        dest='epochs', help='set the max num of epochs')
    parser.add_argument('--interval', action='store', default=10, type=int,
                        dest='interval', help='set the max interval to stop')
    parser.add_argument('--eta', action='store', default=0.001, type=float,
                        dest='eta', help='set the learning rate of training')
    parser.add_argument('--threads', '-t', action='store', default=4, type=int,
                        dest='threads', help='set the max num of threads')
    parser.add_argument('--file', '-f', action='store', default='network.pt',
                        dest='file', help='set where to store the model')
    args = parser.parse_args()

    # 设置随机数种子
    torch.manual_seed(1)
    # 设置最大线程数
    torch.set_num_threads(args.threads)
    print(f"Set max num of threads to {args.threads}")

    # 根据模型读取配置
    config = config.config[args.model]

    print("Preprocess the data")
    # 以训练数据为基础建立语料
    corpus = Corpus(config.ftrain)
    # 用预训练词嵌入扩展语料并返回词嵌入矩阵
    embed = corpus.extend(config.embed)
    print(corpus)

    print("Load the dataset")
    trainset = corpus.load(config.ftrain, config.charwise, config.window)
    devset = corpus.load(config.fdev, config.charwise, config.window)
    testset = corpus.load(config.ftest, config.charwise, config.window)
    print(f"{'':2}size of trainset: {len(trainset)}\n"
          f"{'':2}size of devset: {len(devset)}\n"
          f"{'':2}size of testset: {len(testset)}\n")

    start = datetime.now()

    print("Create Neural Network")
    if args.model == 'lstm':
        print(f"{'':2}vocdim: {corpus.nw}\n"
              f"{'':2}embdim: {config.embdim}\n"
              f"{'':2}hiddim: {config.hiddim}\n"
              f"{'':2}outdim: {corpus.nt}\n")
        network = LSTM(vocdim=corpus.nw,
                       embdim=config.embdim,
                       hiddim=config.hiddim,
                       outdim=corpus.nt,
                       lossfn=nn.CrossEntropyLoss(),
                       embed=embed,
                       crf=args.crf,
                       p=args.prob)
    elif args.model == 'lstm_char':
        print(f"{'':2}vocdim: {corpus.nw}\n"
              f"{'':2}chrdim: {corpus.nc}\n"
              f"{'':2}embdim: {config.embdim}\n"
              f"{'':2}char_hiddim: {config.char_hiddim}\n"
              f"{'':2}hiddim: {config.hiddim}\n"
              f"{'':2}outdim: {corpus.nt}\n")
        network = LSTM_CHAR(vocdim=corpus.nw,
                            chrdim=corpus.nc,
                            embdim=config.embdim,
                            char_hiddim=config.char_hiddim,
                            hiddim=config.hiddim,
                            outdim=corpus.nt,
                            lossfn=nn.CrossEntropyLoss(),
                            embed=embed,
                            crf=args.crf,
                            p=args.prob)
    elif args.model == 'bpnn':
        print(f"{'':2}window: {config.window}\n"
              f"{'':2}vocdim: {corpus.nw}\n"
              f"{'':2}embdim: {config.embdim}\n"
              f"{'':2}hiddim: {config.hiddim}\n"
              f"{'':2}outdim: {corpus.nt}\n")
        network = BPNN(window=config.window,
                       vocdim=corpus.nw,
                       embdim=config.embdim,
                       hiddim=config.hiddim,
                       outdim=corpus.nt,
                       lossfn=nn.CrossEntropyLoss(),
                       embed=embed,
                       crf=args.crf,
                       p=args.prob)
    else:
        print(f"{'':2}vocdim: {corpus.nw}\n"
              f"{'':2}chrdim: {corpus.nc}\n"
              f"{'':2}embdim: {config.embdim}\n"
              f"{'':2}char_hiddim: {config.char_hiddim}\n"
              f"{'':2}outdim: {corpus.nt}\n")
        network = Network(vocdim=corpus.nw,
                          chrdim=corpus.nc,
                          embdim=config.embdim,
                          char_hiddim=config.char_hiddim,
                          outdim=corpus.nt,
                          lossfn=nn.CrossEntropyLoss(),
                          embed=embed,
                          crf=args.crf,
                          p=args.prob)
    print(f"{network}\n")

    # 设置数据加载器
    train_loader = DataLoader(dataset=trainset,
                              batch_size=args.batch_size,
                              shuffle=True,
                              collate_fn=network.collate_fn)
    dev_loader = DataLoader(dataset=devset,
                            batch_size=args.batch_size,
                            collate_fn=network.collate_fn)
    test_loader = DataLoader(dataset=testset,
                             batch_size=args.batch_size,
                             collate_fn=network.collate_fn)

    print("Use Adam optimizer to train the network")
    print(f"{'':2}epochs: {args.epochs}\n"
          f"{'':2}batch_size: {args.batch_size}\n"
          f"{'':2}interval: {args.interval}\n"
          f"{'':2}eta: {args.eta}\n")
    network.fit(train_loader=train_loader,
                dev_loader=dev_loader,
                epochs=args.epochs,
                interval=args.interval,
                eta=args.eta,
                file=args.file)

    # 载入训练好的模型
    network = torch.load(args.file)
    loss, tp, total, accuracy = network.evaluate(test_loader)
    print(f"{'test:':<6} "
          f"Loss: {loss:.4f} "
          f"Accuracy: {tp} / {total} = {accuracy:.2%}")
    print(f"{datetime.now() - start}s elapsed\n")
